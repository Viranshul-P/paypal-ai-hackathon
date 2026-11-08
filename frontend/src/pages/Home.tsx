import { ChevronRight, Send, Users, type LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';

import { PayerShell } from '../components/PayerShell';
import { Card } from '../components/ui/Card';
import { useConfig } from '../lib/config';
import { useI18n } from '../lib/i18n';

function Door({ to, icon: Icon, title, body, strong }: { to: string; icon: LucideIcon; title: string; body: string; strong?: boolean }) {
  return (
    <Link to={to} className={`flex items-center gap-3 rounded-card p-4 no-underline shadow-card ${strong ? 'bg-action text-white hover:bg-action-press' : 'bg-card text-ink hover:bg-tint'}`}>
      <span className={`flex size-13 shrink-0 items-center justify-center rounded-full ${strong ? 'bg-white text-action' : 'bg-action-soft text-action'}`}>
        <Icon className="size-6" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-xl leading-tight font-extrabold">{title}</span>
        <span className={`block leading-snug ${strong ? 'text-white' : 'text-ink-2'}`}>{body}</span>
      </span>
      <ChevronRight className="size-6 shrink-0" aria-hidden />
    </Link>
  );
}

function Results() {
  const rows = [
    ['Scams caught', '56%', '95%'],
    ['Scams held for family', '0%', '74%'],
    ['Legitimate payments held', '0%', '0%'],
    ['Legitimate payments flagged', '39%', '17%'],
  ];
  return (
    <div>
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="text-ink-2">
            <th className="py-1.5 pr-2 font-semibold">Tested on 75 scenarios</th>
            <th className="px-2 py-1.5 text-right font-semibold">Bank-style rules</th>
            <th className="py-1.5 pl-2 text-right font-extrabold text-ink">Pauseline</th>
          </tr>
        </thead>
        <tbody className="tabular">
          {rows.map(([name, bank, ours]) => (
            <tr key={name} className="border-t border-line">
              <td className="py-1.5 pr-2">{name}</td>
              <td className="px-2 py-1.5 text-right text-ink-2">{bank}</td>
              <td className="py-1.5 pl-2 text-right text-lg font-extrabold">{ours}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-sm text-ink-2">Held-out test split of our own synthetic benchmark. No real users or real money yet.</p>
    </div>
  );
}

function Rail() {
  return (
    <div>
      <h1 className="text-7xl leading-[1.02] font-extrabold">A pause before money leaves.</h1>
      <p className="mt-5 text-xl text-ink-2">
        Scammers don't steal passwords any more. They talk people into sending the money themselves. Pauseline spots that pressure, has PayPal hold the payment, and asks someone you trust first.
      </p>
      <Card className="mt-8">
        <Results />
      </Card>
    </div>
  );
}

export default function Home() {
  const { t } = useI18n();
  const config = useConfig();
  const steps = [
    t('You pay as usual and say what it is for, by voice or text.', 'आप हमेशा की तरह पेमेंट करते हैं और बोलकर या लिखकर बताते हैं कि यह किसलिए है।'),
    t('Pauseline looks for signs of a scam, and asks if unsure.', 'Pauseline ठगी के संकेत देखता है, और शक होने पर पूछता है।'),
    t('PayPal holds the money. Nothing is taken yet.', 'PayPal पैसे रोककर रखता है। अभी कुछ नहीं कटता।'),
    t(`Normal payments go at once. Risky ones wait for ${config.contact_name}.`, `सामान्य पेमेंट तुरंत चले जाते हैं। जोखिम वाले पेमेंट ${config.contact_name} की जांच तक रुकते हैं।`),
  ];

  return (
    <PayerShell rail={<Rail />}>
      <div className="space-y-3">
        <div className="px-1">
          <h1 className="text-[2.5rem] font-extrabold lg:text-[2.2rem]">{t(`Hello, ${config.payer_name}`, `नमस्ते, ${config.payer_name}`)}</h1>
          <p className="text-lg text-ink-2">{t('Most payments go straight through.', 'ज़्यादातर पेमेंट तुरंत चले जाते हैं।')}</p>
        </div>

        <Door strong to="/send" icon={Send} title={t('Send money', 'पैसे भेजें')} body={t('We check it for scams first', 'पहले हम ठगी की जांच करते हैं')} />
        <Door to="/family" icon={Users} title={t('Family view', 'फ़ैमिली व्यू')} body={t(`For ${config.contact_name}: paused payments`, `${config.contact_name} के लिए: रुके हुए पेमेंट`)} />

        <Card>
          <h2 className="text-2xl font-extrabold">{t('How it works', 'यह कैसे काम करता है')}</h2>
          <ol className="mt-3 list-none space-y-3 p-0">
            {steps.map((step, i) => (
              <li key={step} className="flex gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-tint font-extrabold text-ink-2">{i + 1}</span>
                <span className="leading-snug">{step}</span>
              </li>
            ))}
          </ol>
        </Card>

        <Card className="lg:hidden">
          <Results />
        </Card>

        <p className="px-1 text-sm text-ink-2">
          {t("This runs in PayPal's test environment, so no real money moves.", 'यह PayPal के टेस्ट माहौल में चलता है, इसलिए असली पैसे नहीं जाते।')}{' '}
          {config.cloud_ai
            ? t('What you type is checked by our own model and by an AI model hosted by Groq.', 'आपका लिखा हमारे मॉडल और Groq पर चलने वाले AI मॉडल से जांचा जाता है।')
            : t('What you type is checked on this server and is not sent to any AI company.', 'आपका लिखा इसी सर्वर पर जांचा जाता है और किसी AI कंपनी को नहीं भेजा जाता।')}{' '}
          {t('AI never sends money by itself: a fixed rule or your family decides.', 'AI खुद पैसे नहीं भेजता: एक तय नियम या आपका परिवार फ़ैसला करता है।')}
        </p>
      </div>
    </PayerShell>
  );
}
