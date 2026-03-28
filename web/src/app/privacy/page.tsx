export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto py-8 space-y-8">
      <h1 className="text-3xl font-bold">Privacy Policy</h1>
      <p className="text-muted-foreground">Last updated: March 15, 2026</p>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">1. Information We Collect</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            <strong>Account information:</strong> Email address provided during
            registration
          </li>
          <li>
            <strong>YouTube public data:</strong> Publicly available channel
            metadata, video statistics, and public comments accessed through
            the YouTube Data API
          </li>
          <li>
            <strong>Usage data:</strong> Basic analytics about how you interact
            with the Service
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">2. Purpose of Collection</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>To provide AI-powered YouTube channel analysis</li>
          <li>To generate reports and insights for your channels</li>
          <li>To improve the Service and user experience</li>
          <li>To communicate important service updates</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">3. Data Retention</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            <strong>YouTube API data:</strong> Raw statistics and comments are
            automatically deleted after 30 days in compliance with YouTube API
            Terms of Service
          </li>
          <li>
            <strong>AI-generated content:</strong> Summaries and reports are
            retained as derivative works for as long as your account is active
          </li>
          <li>
            <strong>Account information:</strong> Retained until you request
            account deletion
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">4. Third-Party Services</h2>
        <p>We use the following third-party services to operate:</p>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            <strong>Supabase:</strong> Authentication and database hosting
          </li>
          <li>
            <strong>Google Gemini API:</strong> AI-powered video analysis and
            content summarization
          </li>
          <li>
            <strong>YouTube Data API:</strong> Accessing publicly available
            YouTube data
          </li>
        </ul>
        <p>
          Each third-party service has its own privacy policy governing data
          handling. Please review{" "}
          <a
            href="https://policies.google.com/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-foreground"
          >
            Google&apos;s Privacy Policy
          </a>{" "}
          for information on how Google handles data accessed through its APIs.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">5. Your Rights</h2>
        <p>You have the right to:</p>
        <ul className="list-disc pl-6 space-y-1">
          <li>Access the personal data we hold about you</li>
          <li>Request correction of inaccurate data</li>
          <li>Request deletion of your account and associated data</li>
          <li>Export your data in a portable format</li>
        </ul>
        <p>
          To exercise these rights, please contact us using the information
          below.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">6. Cookies</h2>
        <p>
          The Service uses essential cookies for authentication and session
          management. We do not use third-party tracking cookies or advertising
          cookies.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">7. Comment Data Privacy</h2>
        <p>
          YouTube comment authors are anonymized through hashing before storage.
          We do not store identifiable commenter names or profile information.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">8. Contact</h2>
        <p>
          For privacy-related inquiries or to exercise your data rights, please
          contact us at{" "}
          <span className="font-medium">privacy@tubeagent.com</span>.
        </p>
      </section>
    </div>
  );
}
