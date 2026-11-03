// Sign in with email + password, or (Demo mode) one tap on a labelled sample identity.
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { useLogin, useSampleIdentities, useSampleLogin } from '@/api/hooks';
import { Field, useErrorText } from '@/components/forms';
import { Brand } from '@/components/Logo';
import { PressScale } from '@/components/motion';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Button, Panel, Section, StateView, Tag } from '@/components/ui';
import { useT } from '@/i18n';
import { colors, space } from '@/theme';

export default function SignIn() {
  const { t, pick } = useT();
  const { role } = useLocalSearchParams<{ role?: 'client' | 'worker' }>();
  const samples = useSampleIdentities();
  const sampleLogin = useSampleLogin();
  const login = useLogin();
  const errorText = useErrorText();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const done = () => router.replace('/');
  const [showAll, setShowAll] = useState(false);
  // "I want work" shows workers, "I want to hire" shows clients; the rest (incl. the reviewer) on request.
  const all = samples.data ?? [];
  const shown = showAll || !role ? all : all.filter((s) => s.role === role);
  const hidden = all.length - shown.length;

  return (
    <Screen title={t('auth.signInTitle')} back>
      <Brand tagline={false} />
      <Section title={t('auth.sampleTitle')}>
        {samples.isPending ? <StateView state="loading" /> : null}
        {samples.isError ? <StateView state="error" message={errorText(samples.error) ?? undefined} /> : null}
        {shown.map((s) => (
          <PressScale
            key={s.user_id}
            accessibilityRole="button"
            accessibilityLabel={`${t('auth.sampleBadge')}: ${s.display_name}`}
            disabled={sampleLogin.isPending}
            onPress={() => sampleLogin.mutate({ user_id: s.user_id }, { onSuccess: done })}
          >
            <Panel tone="clay">
              <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
                <Tag tone="demo" label={t('auth.sampleBadge')} />
                <Tag icon={s.role === 'client' ? 'work' : s.role === 'worker' ? 'brush' : 'shield'}
                     label={s.role === 'client' ? t('auth.asClient') : s.role === 'worker' ? t('auth.asWorker') : t('auth.asAdmin')} />
              </View>
              <Txt variant="h3">{s.display_name}</Txt>
              <Txt variant="small" color={colors.inkSoft}>{pick(s.note_ne, s.note_en)}</Txt>
            </Panel>
          </PressScale>
        ))}
        {hidden > 0 ? <Button kind="quiet" label={t('auth.showAllSamples')} onPress={() => setShowAll(true)} /> : null}
        {sampleLogin.isError ? <Txt color={colors.brick}>{errorText(sampleLogin.error)}</Txt> : null}
      </Section>

      <Panel>
        <Field label={t('auth.email')} value={email} onChangeText={setEmail} autoCapitalize="none"
               keyboardType="email-address" autoComplete="email" />
        <Field label={t('auth.password')} value={password} onChangeText={setPassword} secureTextEntry
               autoComplete="password" />
        {login.isError ? <Txt color={colors.brick}>{errorText(login.error, { '401': t('auth.wrongLogin') })}</Txt> : null}
        <Button icon="lock" label={t('auth.signIn')} busy={login.isPending} disabled={!email || !password}
                onPress={() => login.mutate({ email: email.trim(), password }, { onSuccess: done })} />
      </Panel>
      <Button kind="quiet" label={t('auth.noAccount')}
              onPress={() => router.push({ pathname: '/sign-up', params: { role: role ?? 'worker' } })} />
    </Screen>
  );
}
