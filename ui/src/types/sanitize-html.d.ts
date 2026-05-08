declare module 'sanitize-html' {
  interface IOptions {
    allowedTags?: string[] | false;
    allowedAttributes?: Record<string, string[]> | false;
    allowedSchemes?: string[];
    [key: string]: any;
  }
  function sanitizeHtml(dirty: string, options?: IOptions): string;
  export = sanitizeHtml;
}
