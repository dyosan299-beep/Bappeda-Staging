import React from "react";

/** Logo PETA INKLUSI. variant: "icon" (pin saja) | "full" (dengan tulisan). */
export default function BrandLogo({ variant = "icon", className = "h-10 w-10", withText = false, dark = true }) {
  const src = variant === "full" ? "/logo-peta-inklusi.png" : "/logo-icon.png";
  return (
    <span className="inline-flex min-w-0 items-center gap-2 sm:gap-2.5">
      <img src={src} alt="Logo PETA INKLUSI" className={`${className} shrink-0 rounded-lg object-cover`} />
      {withText && (
        <span className="min-w-0 leading-tight">
          <span className={`block whitespace-nowrap font-head text-[15px] font-extrabold tracking-wide sm:text-base ${dark ? "text-[#6FE3CF]" : "text-[#117A69]"}`}>
            PETA INKLUSI
          </span>
          <span className={`block truncate text-[10px] uppercase tracking-wider max-[359px]:hidden ${dark ? "text-slate-300" : "text-slate-500"}`}>
            Bappeda Kota Makassar
          </span>
        </span>
      )}
    </span>
  );
}
