// The error type every API call throws. Its own module so client.ts and the mocks can both use it
// without importing each other.
export class ApiError extends Error {
  constructor(
    public kind: 'network' | 'http' | 'mock',
    public status: number,
    public detail: unknown,
  ) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
}
