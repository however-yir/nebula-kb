declare module 'sanitize-html' {
  interface IOptions {
    allowedTags?: string[] | false;
    allowedAttributes?: Record<string, string[]> | false;
    allowedSchemes?: string[];
    [key: string]: unknown;
  }
  function sanitizeHtml(dirty: string, options?: IOptions): string;
  namespace sanitizeHtml {
    export { IOptions };
  }
  export = sanitizeHtml;
}
