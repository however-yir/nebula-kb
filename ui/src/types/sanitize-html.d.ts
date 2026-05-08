declare module 'sanitize-html' {
  interface SanitizeOptions {
    allowedTags?: string[] | false;
    allowedAttributes?: Record<string, string[]> | false;
    allowedSchemes?: string[];
    [key: string]: unknown;
  }
  function sanitizeHtml(dirty: string, options?: SanitizeOptions): string;
  export default sanitizeHtml;
}
