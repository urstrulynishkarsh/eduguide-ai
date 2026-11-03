/** An unsigned token with the claims the frontend reads (the backend is what checks signatures). */
export function fakeToken(role: "parent" | "student", secondsLeft: number): string {
  const encode = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const exp = Math.floor(Date.now() / 1000) + secondsLeft;
  return `${encode({ alg: "HS256" })}.${encode({ sub: "user-1", role, type: "access", exp })}.signature`;
}
