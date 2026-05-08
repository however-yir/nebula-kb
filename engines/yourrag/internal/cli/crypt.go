//
//  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
//

package cli

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// EncryptPassword encrypts a password using RSA public key
// This matches the Python implementation in api/utils/crypt.py
func EncryptPassword(password string) (string, error) {
	// Step 1: Base64 encode the password
	passwordBase64 := base64.StdEncoding.EncodeToString([]byte(password))

	publicKeyPEM, err := loadPublicKeyPEM()
	if err != nil {
		// Fallback: transport as base64-only when RSA key is not configured.
		return passwordBase64, nil
	}

	// Parse public key
	block, _ := pem.Decode(publicKeyPEM)
	if block == nil {
		return passwordBase64, nil
	}

	pub, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		// Try parsing as PKCS1
		pub, err = x509.ParsePKCS1PublicKey(block.Bytes)
		if err != nil {
			return passwordBase64, nil
		}
	}

	rsaPub, ok := pub.(*rsa.PublicKey)
	if !ok {
		return "", fmt.Errorf("not an RSA public key")
	}

	// Step 2: Encrypt using RSA PKCS1v15
	encrypted, err := rsa.EncryptPKCS1v15(rand.Reader, rsaPub, []byte(passwordBase64))
	if err != nil {
		return "", fmt.Errorf("failed to encrypt password: %w", err)
	}

	// Step 3: Base64 encode the encrypted data
	return base64.StdEncoding.EncodeToString(encrypted), nil
}

func loadPublicKeyPEM() ([]byte, error) {
	// Highest priority: inline PEM from env.
	for _, envName := range []string{"YOURRAG_RSA_PUBLIC_KEY_PEM", "RAGFLOW_RSA_PUBLIC_KEY_PEM"} {
		if pemValue := strings.TrimSpace(os.Getenv(envName)); pemValue != "" {
			return []byte(strings.ReplaceAll(pemValue, `\n`, "\n")), nil
		}
	}

	// Next: configured key path from env.
	for _, envName := range []string{"YOURRAG_RSA_PUBLIC_KEY_PATH", "RAGFLOW_RSA_PUBLIC_KEY_PATH"} {
		if keyPath := strings.TrimSpace(os.Getenv(envName)); keyPath != "" {
			data, err := os.ReadFile(keyPath)
			if err != nil {
				return nil, err
			}
			return data, nil
		}
	}

	// Default path in project.
	publicKeyPath := filepath.Join(getProjectBaseDirectory(), "conf", "public.pem")
	return os.ReadFile(publicKeyPath)
}

// getProjectBaseDirectory returns the project base directory
func getProjectBaseDirectory() string {
	// Try to find the project root by looking for go.mod or conf directory
	// Start from current working directory and go up
	cwd, err := os.Getwd()
	if err != nil {
		return "."
	}

	dir := cwd
	for {
		// Check if conf directory exists
		confDir := filepath.Join(dir, "conf")
		if info, err := os.Stat(confDir); err == nil && info.IsDir() {
			return dir
		}

		// Check for go.mod
		goMod := filepath.Join(dir, "go.mod")
		if _, err := os.Stat(goMod); err == nil {
			return dir
		}

		// Go up one directory
		parent := filepath.Dir(dir)
		if parent == dir {
			// Reached root
			break
		}
		dir = parent
	}

	return cwd
}
