import clsx from 'clsx';
import { useEffect, useState } from 'react';

import { useConfig } from '../../lib/config';
import { speak } from '../../lib/format';
import { useI18n } from '../../lib/i18n';
import type { Question } from '../../lib/types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Notice } from '../ui/Notice';

interface QuestionsStepProps {
  questions: Question[];
  busy: boolean;
  error: string;
  onSubmit: (answers: Record<string, string>) => void;
}

export function QuestionsStep({ questions, busy, error, onSubmit }: QuestionsStepProps) {
  const { t, lang } = useI18n();
  const config = useConfig();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const shown = (q: Question) => (lang === 'hi' ? q.text_hi : q.text);

  useEffect(() => {
    if (questions[0]) speak(lang === 'hi' ? questions[0].text_hi : questions[0].text);
    // Read the first question aloud once, when the step opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const complete = questions.every((q) => answers[q.id]);

  return (
    <div className="space-y-3">
      <div className="px-1">
        <h1 className="text-[2.2rem] font-extrabold">
          {questions.length === 1 ? t('One quick question', 'एक छोटा सवाल') : t(`${questions.length} quick questions`, `${questions.length} छोटे सवाल`)}
        </h1>
        <p className="mt-1 text-lg text-ink-2">
          {t(`Scammers often tell people what to say. Only ${config.contact_name} sees your answers.`, `ठग अक्सर बताते हैं कि क्या बोलना है। आपके जवाब सिर्फ़ ${config.contact_name} देख सकते हैं।`)}
        </p>
      </div>

      {questions.map((q) => (
        <Card key={q.id}>
          <p className="text-[1.35rem] leading-snug font-semibold">{shown(q)}</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {(['yes', 'no'] as const).map((choice) => (
              <button
                key={choice}
                type="button"
                aria-pressed={answers[q.id] === choice}
                onClick={() => setAnswers((a) => ({ ...a, [q.id]: choice }))}
                className={clsx(
                  'min-h-16 rounded-2xl text-xl font-extrabold transition-colors duration-150',
                  answers[q.id] === choice ? 'bg-action text-white' : 'bg-action-soft text-action',
                )}
              >
                {choice === 'yes' ? t('Yes', 'हां') : t('No', 'नहीं')}
              </button>
            ))}
          </div>
        </Card>
      ))}

      {error && <Notice>{error}</Notice>}
      <Button disabled={!complete || busy} onClick={() => onSubmit(answers)}>
        {t('Continue', 'आगे बढ़ें')}
      </Button>
    </div>
  );
}
