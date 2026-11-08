export interface AppConfig {
  paypal_live: boolean;
  paypal_client_id: string;
  currency: string;
  ai_mode: string;
  cloud_ai: boolean;
  demo_pin: string;
  payer_name: string;
  contact_name: string;
  contact_relationship: string;
}

export interface Payee {
  id: string;
  name: string;
  email: string;
  relationship: string;
  known: boolean;
  blocked: boolean;
}

export type TransferStatus = 'draft' | 'awaiting_payer' | 'held' | 'released' | 'cancelled' | 'failed';

export interface Question {
  id: string;
  text: string;
  text_hi: string;
}

export interface Signal {
  name: string;
  label: string;
  evidence: string;
  weight: number;
}

export interface Transfer {
  id: string;
  status: TransferStatus;
  decision: 'allow' | 'cool_off' | 'hold_for_family' | 'block' | null;
  risk: number | null;
  amount: number;
  currency: string;
  payee: Payee;
  statement: string;
  scam_type: string | null;
  message_to_payer: string;
  summary_for_family: string;
  signals: Signal[];
  questions: Question[];
  answers: Record<string, string>;
  authorization_id: string | null;
  release_at: number | null;
  family_decision: string | null;
  family_note: string | null;
  delivery_failed: boolean;
  created_at: number;
  updated_at: number;
}

export interface AppEvent {
  id: number;
  at: number;
  kind: string;
  detail: string;
}

export interface FamilyOverview {
  pending: Transfer[];
  recent: Transfer[];
  events: AppEvent[];
}
