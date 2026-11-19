import { useEffect } from "react";

const SUFFIX = "PETA INKLUSI Bappeda Kota Makassar";

/**
 * Menyetel <title> unik dan deskriptif per halaman (WCAG 2.4.2).
 * Tanpa dependency tambahan; cukup dipanggil sekali per layout/halaman.
 */
export function usePageTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} | ${SUFFIX}` : SUFFIX;
  }, [title]);
}

export default usePageTitle;
