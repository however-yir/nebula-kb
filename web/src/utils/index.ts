/**
 * @param  {String}  url
 * @param  {Boolean} isNoCaseSensitive 是否区分大小写
 * @return {Object}
 */
// import numeral from 'numeral';

import { Base64 } from 'js-base64';
import JSEncrypt from 'jsencrypt';

export const getWidth = () => {
  return { width: window.innerWidth };
};
export const rsaPsw = (password: string) => {
  const passwordBase64 = Base64.encode(password);
  const publicKey =
    import.meta.env.VITE_RSA_PUBLIC_KEY?.replace(/\\n/g, '\n').trim() || '';
  if (!publicKey) {
    return passwordBase64;
  }
  const encryptor = new JSEncrypt();
  encryptor.setPublicKey(publicKey);
  return encryptor.encrypt(passwordBase64) || passwordBase64;
};

export default {
  getWidth,
  rsaPsw,
};

export const getFileExtension = (filename: string) =>
  filename.slice(filename.lastIndexOf('.') + 1).toLowerCase();
