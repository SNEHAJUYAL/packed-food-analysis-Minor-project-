import { vi } from "vitest";

export const routerPush = vi.fn();

export const navigation = {
  useRouter: () => ({ push: routerPush, replace: vi.fn(), prefetch: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
};
