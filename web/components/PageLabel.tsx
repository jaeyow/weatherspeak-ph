'use client';

import { useTranslation } from './LanguageProvider';
import type { TranslationKey } from '@/lib/translations';

interface Props {
  k: TranslationKey;
  className?: string;
}

export default function PageLabel({ k, className }: Props) {
  const { t } = useTranslation();
  return <span className={className}>{t(k)}</span>;
}
