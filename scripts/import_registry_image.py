#!/usr/bin/env python3
import argparse
import gzip
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


MANIFEST_LIST_TYPES = (
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
)
MANIFEST_TYPES = (
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
)
ALL_MANIFEST_TYPES = ",".join(MANIFEST_LIST_TYPES + MANIFEST_TYPES)


def parse_image_ref(ref: str):
    registry = "registry-1.docker.io"
    remainder = ref
    if "/" in ref and ("." in ref.split("/")[0] or ":" in ref.split("/")[0]):
        registry, remainder = ref.split("/", 1)
    if ":" in remainder.rsplit("/", 1)[-1]:
        repository, tag = remainder.rsplit(":", 1)
    else:
        repository, tag = remainder, "latest"
    if registry == "registry-1.docker.io" and "/" not in repository:
        repository = f"library/{repository}"
    return registry, repository, tag


def dockerhub_token(repository: str) -> str:
    query = urlencode(
        {
            "service": "registry.docker.io",
            "scope": f"repository:{repository}:pull",
        }
    )
    with urlopen(f"https://auth.docker.io/token?{query}") as response:
        return json.load(response)["token"]


def request_json(url: str, token: str, accept: str):
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": accept})
    with urlopen(request) as response:
        return json.load(response), response.headers.get("Content-Type", "")


def stream_blob(url: str, token: str):
    class NoRedirectHandler(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = build_opener(NoRedirectHandler)
    request = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        return opener.open(request)
    except HTTPError as exc:
        if exc.code not in {301, 302, 303, 307, 308}:
            raise
        redirect_url = exc.headers.get("Location")
        if not redirect_url:
            raise
        return urlopen(Request(redirect_url))


def download_blob(url: str, token: str, destination: Path):
    subprocess.run(
        [
            "curl",
            "-fsSL",
            "-H",
            f"Authorization: Bearer {token}",
            url,
            "-o",
            str(destination),
        ],
        check=True,
    )


def select_manifest(manifest_index: dict, arch: str) -> str:
    manifests = manifest_index.get("manifests", [])
    for manifest in manifests:
        platform = manifest.get("platform", {})
        if platform.get("os") == "linux" and platform.get("architecture") == arch:
            return manifest["digest"]
    raise SystemExit(f"No linux/{arch} manifest found")


def ensure_within(root: Path, target: Path):
    target.resolve().relative_to(root.resolve())


def remove_path(target: Path):
    if target.is_symlink() or target.is_file():
        target.unlink(missing_ok=True)
    elif target.is_dir():
        shutil.rmtree(target, ignore_errors=True)


def apply_layer(blob_path: Path, rootfs: Path):
    with gzip.open(blob_path, "rb") as gz:
        with tarfile.open(fileobj=gz, mode="r|") as archive:
            for member in archive:
                if not member.name:
                    continue
                path = Path(member.name)
                if path.is_absolute():
                    path = Path(str(path).lstrip("/"))
                if ".." in path.parts:
                    continue
                basename = path.name
                parent = rootfs / path.parent
                target = rootfs / path
                ensure_within(rootfs, parent)
                ensure_within(rootfs, target)

                if basename == ".wh..wh..opq":
                    if parent.exists():
                        for child in parent.iterdir():
                            remove_path(child)
                    continue
                if basename.startswith(".wh."):
                    remove_path(parent / basename[4:])
                    continue

                parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.chmod(parent, parent.stat().st_mode | 0o700)
                except OSError:
                    pass
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.issym():
                    remove_path(target)
                    os.symlink(member.linkname, target)
                elif member.islnk():
                    remove_path(target)
                    link_target = rootfs / member.linkname
                    ensure_within(rootfs, link_target)
                    os.link(link_target, target)
                elif member.isfile():
                    remove_path(target)
                    with archive.extractfile(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                else:
                    continue

                try:
                    if not member.issym() and not member.isdir():
                        os.chmod(target, member.mode)
                except FileNotFoundError:
                    pass


def create_rootfs_tar(rootfs: Path, output_path: Path):
    with tarfile.open(output_path, "w") as archive:
        for path in sorted(rootfs.rglob("*")):
            arcname = str(path.relative_to(rootfs))
            archive.add(path, arcname=arcname, recursive=False)


def json_array(value):
    return json.dumps(value, separators=(",", ":"))


def import_image(rootfs_tar: Path, target_ref: str, config: dict):
    command = ["docker", "import"]
    for env in config.get("config", {}).get("Env", []) or []:
        command.extend(["--change", f"ENV {env}"])
    if config.get("config", {}).get("WorkingDir"):
        command.extend(["--change", f"WORKDIR {config['config']['WorkingDir']}"])
    if config.get("config", {}).get("User"):
        command.extend(["--change", f"USER {config['config']['User']}"])
    for port in (config.get("config", {}).get("ExposedPorts") or {}).keys():
        command.extend(["--change", f"EXPOSE {port}"])
    for volume in (config.get("config", {}).get("Volumes") or {}).keys():
        command.extend(["--change", f"VOLUME {volume}"])
    if config.get("config", {}).get("Entrypoint") is not None:
        command.extend(["--change", f"ENTRYPOINT {json_array(config['config']['Entrypoint'])}"])
    if config.get("config", {}).get("Cmd") is not None:
        command.extend(["--change", f"CMD {json_array(config['config']['Cmd'])}"])
    command.extend([str(rootfs_tar), target_ref])
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(description="Import a public registry image into local Docker using host networking")
    parser.add_argument("source", help="Image reference, for example postgres:16")
    parser.add_argument("--target", help="Target local tag; defaults to source reference")
    parser.add_argument("--arch", default="arm64", help="Target architecture, default arm64")
    args = parser.parse_args()

    registry, repository, tag = parse_image_ref(args.source)
    if registry != "registry-1.docker.io":
        raise SystemExit("Only Docker Hub references are supported by this helper")

    token = dockerhub_token(repository)
    manifest_url = f"https://{registry}/v2/{repository}/manifests/{tag}"
    print(f"Resolving {args.source} from docker.io/{repository}:{tag}", flush=True)
    manifest, content_type = request_json(manifest_url, token, ALL_MANIFEST_TYPES)
    if any(media_type in content_type for media_type in MANIFEST_LIST_TYPES):
        digest = select_manifest(manifest, args.arch)
        print(f"Selected manifest {digest} for linux/{args.arch}", flush=True)
        manifest, _ = request_json(
            f"https://{registry}/v2/{repository}/manifests/{digest}",
            token,
            ",".join(MANIFEST_TYPES),
        )

    config_digest = manifest["config"]["digest"]
    print(f"Downloading config {config_digest}", flush=True)
    with stream_blob(f"https://{registry}/v2/{repository}/blobs/{config_digest}", token) as response:
        config = json.load(response)

    target_ref = args.target or args.source
    with tempfile.TemporaryDirectory(prefix="registry-import-") as temp_dir:
        temp_path = Path(temp_dir)
        rootfs = temp_path / "rootfs"
        rootfs.mkdir()
        layers = manifest.get("layers", [])
        print(f"Applying {len(layers)} layers into local rootfs", flush=True)
        for index, layer in enumerate(layers, start=1):
            digest = layer["digest"]
            blob_path = temp_path / f"layer-{index}.tar.gz"
            print(f"[{index}/{len(layers)}] Downloading {digest}", flush=True)
            download_blob(f"https://{registry}/v2/{repository}/blobs/{digest}", token, blob_path)
            print(f"[{index}/{len(layers)}] Extracting {digest}", flush=True)
            apply_layer(blob_path, rootfs)
        rootfs_tar = temp_path / "rootfs.tar"
        print("Packing rootfs tar", flush=True)
        create_rootfs_tar(rootfs, rootfs_tar)
        print(f"Importing into local Docker as {target_ref}", flush=True)
        import_image(rootfs_tar, target_ref, config)
        print(f"Imported {target_ref}", flush=True)


if __name__ == "__main__":
    main()
