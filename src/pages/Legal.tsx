import { Panel, Eyebrow } from "../components/ui";

type Doc = { title: string; updated: string; intro: string; sections: { h: string; body: string }[] };

const privacy: Doc = {
  title: "Privacy Policy",
  updated: "2026-09-15",
  intro:
    "This policy describes how Satya Dristi processes information in this demonstration environment. Sections marked [ORGANIZATION] require organization-specific legal wording before operational use.",
  sections: [
    { h: "Information collected", body: "We process the imagery you upload, the natural-language queries you submit, and technical usage information required to operate the service." },
    { h: "Uploaded imagery", body: "Uploaded scenes are used to perform the requested analysis. Retention behavior is configurable in Settings → Privacy. [ORGANIZATION] must specify operational retention periods." },
    { h: "Query information", body: "Query text may be stored to support history, search, and auditability, subject to your Settings selections." },
    { h: "Usage information", body: "We record limited operational metadata (timestamps, task type, execution metrics) to maintain and improve reliability." },
    { h: "Data processing", body: "Analysis is performed by specialist remote-sensing models. Observable execution metadata is retained; internal model reasoning is not recorded." },
    { h: "Data retention", body: "Retention is governed by your configured preferences. [ORGANIZATION] must define maximum retention and deletion procedures." },
    { h: "Security", body: "Access controls and encryption are applied to stored data. [ORGANIZATION] must document its specific security controls and certifications." },
    { h: "Third-party services", body: "Where third-party infrastructure is used, it is listed here. [ORGANIZATION] must enumerate processors and sub-processors." },
    { h: "User rights", body: "You may request access to, correction of, or deletion of your data through the channels defined by [ORGANIZATION]." },
    { h: "Contact", body: "Direct privacy enquiries to the contact address published by [ORGANIZATION]." },
  ],
};

const terms: Doc = {
  title: "Terms & Conditions",
  updated: "2026-09-15",
  intro:
    "These terms govern use of the Satya Dristi demonstration interface. Sections marked [ORGANIZATION] require organization-specific legal wording before operational use.",
  sections: [
    { h: "Acceptance of terms", body: "By accessing the platform you agree to these terms. If you do not agree, do not use the service." },
    { h: "Platform usage", body: "The platform is provided for remote-sensing analysis workflows. You are responsible for the lawfulness of the imagery you submit." },
    { h: "Uploaded data", body: "You retain rights to imagery you upload. You grant the platform the limited rights necessary to perform requested analysis." },
    { h: "AI-generated analysis", body: "Analysis outputs are produced by automated models and are provided as decision-support, not as authoritative determinations." },
    { h: "Accuracy and uncertainty", body: "Outputs carry inherent uncertainty. Confidence indicators reflect agreement between specialist predictions and must not be read as guarantees." },
    { h: "Acceptable use", body: "You must not use the platform for unlawful purposes or in violation of applicable export, privacy, or data-protection regulations." },
    { h: "Intellectual property", body: "Platform software, interfaces, and model artifacts remain the property of [ORGANIZATION] and its licensors." },
    { h: "Service availability", body: "The service is provided on an as-available basis. [ORGANIZATION] does not warrant uninterrupted availability." },
    { h: "Limitation of liability", body: "To the extent permitted by law, [ORGANIZATION] is not liable for decisions made in reliance on analysis outputs." },
    { h: "Changes to terms", body: "These terms may be updated. Material changes will be communicated through the platform." },
    { h: "Contact", body: "Direct enquiries regarding these terms to the contact address published by [ORGANIZATION]." },
  ],
};

export function Legal({ kind }: { kind: "privacy" | "terms" }) {
  const doc = kind === "privacy" ? privacy : terms;
  return (
    <div className="mx-auto max-w-3xl">
      <header className="border-b border-border pb-5">
        <Eyebrow>Legal · demonstration</Eyebrow>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">{doc.title}</h1>
        <p className="mono mt-1 text-[11px] text-muted-foreground">Last updated {doc.updated}</p>
        <p className="mt-4 text-[13.5px] leading-relaxed text-muted-foreground">{doc.intro}</p>
      </header>

      <div className="mt-6 grid gap-4 md:grid-cols-[180px_1fr]">
        <nav className="sticky top-20 hidden h-fit md:block">
          <Eyebrow>Contents</Eyebrow>
          <ol className="mt-2 space-y-1.5">
            {doc.sections.map((s, i) => (
              <li key={s.h}>
                <a href={`#s${i}`} className="mono text-[11px] text-muted-foreground hover:text-accent">
                  {String(i + 1).padStart(2, "0")} · {s.h}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <Panel className="divide-y divide-border p-0">
          {doc.sections.map((s, i) => (
            <section key={s.h} id={`s${i}`} className="scroll-mt-20 p-5">
              <div className="flex items-baseline gap-2.5">
                <span className="mono text-[11px] text-accent">{String(i + 1).padStart(2, "0")}</span>
                <h2 className="text-[15px] font-semibold">{s.h}</h2>
              </div>
              <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{s.body}</p>
            </section>
          ))}
        </Panel>
      </div>
    </div>
  );
}
