export default function Logo({ size = 32 }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true">
      <path d="M32 3 L57 11 V30 C57 46 46 57 32 61 C18 57 7 46 7 30 V11 Z" fill="#0E9F8E" />
      <rect x="19" y="19" width="26" height="17" rx="5" fill="#fff" />
      <path d="M25 35 L25 43 L33 35 Z" fill="#fff" />
      <path d="M26 27.5 L30.5 32 L38.5 23.5" fill="none" stroke="#0E9F8E" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
