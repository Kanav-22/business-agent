import type { SVGProps } from "react";

export function LogoMark({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
      {...props}
    >
      <path
        d="M24 3.75 41.54 13.88v20.24L24 44.25 6.46 34.12V13.88L24 3.75Z"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity=".56"
      />
      <path
        d="m24 14.5 8.23 4.75v9.5L24 33.5l-8.23-4.75v-9.5L24 14.5Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M24 14.5V8.25M32.23 19.25l5.38-3.1M32.23 28.75l5.38 3.1M24 33.5v6.25M15.77 28.75l-5.38 3.1M15.77 19.25l-5.38-3.1"
        stroke="currentColor"
        strokeWidth="1.25"
        opacity=".72"
      />
      <circle cx="24" cy="24" r="3.4" fill="currentColor" />
      <circle cx="24" cy="8.25" r="1.7" fill="currentColor" />
      <circle cx="37.61" cy="16.15" r="1.7" fill="currentColor" />
      <circle cx="37.61" cy="31.85" r="1.7" fill="currentColor" />
      <circle cx="24" cy="39.75" r="1.7" fill="currentColor" />
      <circle cx="10.39" cy="31.85" r="1.7" fill="currentColor" />
      <circle cx="10.39" cy="16.15" r="1.7" fill="currentColor" />
    </svg>
  );
}
