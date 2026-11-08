import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';

import { PayerShell } from '../components/PayerShell';
import { StoryRail } from '../components/StoryRail';
import { DetailsStep, NEW_PAYEE, type Details } from '../components/send/DetailsStep';
import { PayStep } from '../components/send/PayStep';
import { QuestionsStep } from '../components/send/QuestionsStep';
import { ResultStep, useOutcome } from '../components/send/ResultStep';
import { api } from '../lib/api';
import { speak } from '../lib/format';
import type { Payee, Transfer } from '../lib/types';

type Step = 'details' | 'questions' | 'pay' | 'result';

const RAIL_POSITION: Record<Step, number> = { details: 0, questions: 1, pay: 2, result: 3 };

export default function Send() {
  const [payees, setPayees] = useState<Payee[]>([]);
  const [step, setStep] = useState<Step>('details');
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  // Retrying after an error must not add the same new person twice.
  const createdPayee = useRef<Payee | null>(null);
  const outcomeFor = useOutcome();

  useEffect(() => {
    api<Payee[]>('/api/payees').then(setPayees, (e) => setError(e.message));
  }, []);

  // While a payment is on hold, wait for the family's decision.
  const heldId = transfer?.status === 'held' ? transfer.id : null;
  useEffect(() => {
    if (!heldId) return;
    const timer = setInterval(async () => {
      try {
        const fresh = await api<Transfer>(`/api/transfers/${heldId}`);
        if (fresh.status !== 'held') setTransfer(fresh);
      } catch {
        /* try again on the next tick */
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [heldId]);

  function go(next: Step) {
    setError('');
    setStep(next);
    document.querySelector('main')?.scrollTo({ top: 0 });
  }

  function afterAssessment(t: Transfer) {
    if (t.decision && t.decision !== 'allow' && t.message_to_payer && !t.questions.length) speak(t.message_to_payer);
    go('pay');
  }

  async function submitDetails(d: Details) {
    setBusy(true);
    setError('');
    try {
      let payeeId = d.payeeId;
      if (payeeId === NEW_PAYEE) {
        const prior = createdPayee.current;
        if (!prior || prior.name !== d.newName || prior.email !== d.newEmail) {
          createdPayee.current = await api<Payee>('/api/payees', { method: 'POST', body: { name: d.newName, email: d.newEmail, known: false } });
        }
        payeeId = createdPayee.current!.id;
      }
      const t = await api<Transfer>('/api/transfers', { method: 'POST', body: { payee_id: payeeId, amount: d.amount, statement: d.statement } });
      setTransfer(t);
      if (t.questions.length) go('questions');
      else afterAssessment(t);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  }

  async function submitAnswers(answers: Record<string, string>) {
    setBusy(true);
    setError('');
    try {
      const t = await api<Transfer>(`/api/transfers/${transfer!.id}/answers`, { method: 'POST', body: { answers } });
      setTransfer(t);
      afterAssessment(t);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  }

  async function createOrder() {
    const r = await api<{ order_id: string }>(`/api/transfers/${transfer!.id}/order`, { method: 'POST' });
    return r.order_id;
  }

  async function onApproved() {
    try {
      const t = await api<Transfer>(`/api/transfers/${transfer!.id}/approved`, { method: 'POST' });
      setTransfer(t);
      go('result');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'PayPal could not complete this. You were not charged.');
    }
  }

  async function cancel() {
    try {
      const t = await api<Transfer>(`/api/transfers/${transfer!.id}/cancel`, { method: 'POST' });
      setTransfer(t);
      go('result');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not cancel. Try again.');
    }
  }

  const outcome = step === 'result' && transfer ? outcomeFor(transfer) : null;
  const finished = step === 'result' && transfer !== null && transfer.status !== 'held';

  return (
    <PayerShell held={step === 'result' && transfer?.status === 'held'} rail={<StoryRail current={RAIL_POSITION[step]} done={finished} />}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div key={step} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }}>
          {step === 'details' && <DetailsStep payees={payees} busy={busy} error={error} onError={setError} onContinue={submitDetails} />}
          {step === 'questions' && transfer && <QuestionsStep questions={transfer.questions} busy={busy} error={error} onSubmit={submitAnswers} />}
          {step === 'pay' && transfer && <PayStep transfer={transfer} error={error} createOrder={createOrder} onApproved={onApproved} onFailure={setError} onCancel={cancel} />}
          {step === 'result' && transfer && outcome && <ResultStep transfer={transfer} outcome={outcome} onCancel={cancel} />}
        </motion.div>
      </AnimatePresence>
    </PayerShell>
  );
}
