// Numerals, money and time display. Money always uses Latin digits with a currency code
// so a price can never be misread; counts, days and times follow the user's numerals setting.
export type Locale = 'ne' | 'en';
export type Numerals = 'devanagari' | 'latin';

const DEVANAGARI = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९'];

export function toDevanagariDigits(text: string): string {
  return text.replace(/[0-9]/g, (d) => DEVANAGARI[Number(d)]);
}

export function toLatinDigits(text: string): string {
  return text.replace(/[०-९]/g, (d) => String(DEVANAGARI.indexOf(d)));
}

export function wantsDevanagari(locale: Locale, numerals: Numerals): boolean {
  return locale === 'ne' && numerals === 'devanagari';
}

/**
 * Counts, days, hours: Devanagari in Nepali (unless the user chose Latin digits).
 * Amounts after "$" or "USD" keep Latin digits, so money is never misread.
 */
export function localDigits(text: string | number, locale: Locale, numerals: Numerals): string {
  const s = String(text);
  if (!wantsDevanagari(locale, numerals)) return s;
  return s.replace(/(\$|USD\s?)?([0-9][0-9.,]*)/g, (all, money: string | undefined, num: string) =>
    money ? all : toDevanagariDigits(num),
  );
}

/** Money from integer minor units. Always Latin digits: "$40" or "USD 40.50". Never pass through t(). */
export function money(amountMinor: number, currency: string): string {
  const major = amountMinor / 100;
  const text = Number.isInteger(major) ? String(major) : major.toFixed(2);
  return currency === 'USD' ? `$${text}` : `${currency} ${text}`;
}

/** Whole hours left until an ISO time (never negative). */
export function hoursUntil(iso: string | null | undefined, now: number = Date.now()): number | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - now;
  return Math.max(0, Math.ceil(ms / 3_600_000));
}
