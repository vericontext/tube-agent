import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t bg-background">
      <div className="container mx-auto flex flex-col items-center gap-2 px-4 py-6 text-sm text-muted-foreground md:flex-row md:justify-between">
        <div className="flex items-center gap-4">
          <Link href="/terms" className="hover:text-foreground transition-colors">
            Terms of Service
          </Link>
          <Link href="/privacy" className="hover:text-foreground transition-colors">
            Privacy Policy
          </Link>
        </div>
        <p>Powered by YouTube Data API</p>
        <p>&copy; {new Date().getFullYear()} Tube Agent. All rights reserved.</p>
      </div>
    </footer>
  );
}
