export function withBase(path: string): string {
  if (/^[a-z][a-z0-9+.-]*:/i.test(path)) {
    return path;
  }

  const base = import.meta.env.BASE_URL || '/';
  const normalizedBase = base.endsWith('/') ? base : `${base}/`;
  const normalizedPath = path.replace(/^\/+/, '');

  if (normalizedPath === '') {
    return normalizedBase;
  }

  return `${normalizedBase}${normalizedPath}`;
}

export function absoluteUrl(path: string, origin = 'https://cyberpivots.github.io'): string {
  return new URL(withBase(path), origin).toString();
}

