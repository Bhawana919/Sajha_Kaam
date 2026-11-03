// Sign up. Only what is needed: name, language, skills (worker) or country (client), a login email.
// Never photo, caste, religion, age, gender or citizenship number. Workers attest 18+.
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { useRegister, useSkills } from '@/api/hooks';
import { Checkbox, Field, useErrorText } from '@/components/forms';
import { Screen } from '@/components/Screen';
import { Txt } from '@/components/Txt';
import { Bullet, Button, Chip, Panel, Section } from '@/components/ui';
import { useT } from '@/i18n';
import { colors, space } from '@/theme';

export default function SignUp() {
  const { t, pick, locale } = useT();
  const params = useLocalSearchParams<{ role?: 'client' | 'worker' }>();
  const [role, setRole] = useState<'client' | 'worker'>(params.role === 'client' ? 'client' : 'worker');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [country, setCountry] = useState('');
  const [org, setOrg] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [adult, setAdult] = useState(false);
  const [consent, setConsent] = useState(false);
  const allSkills = useSkills();
  const register = useRegister();
  const errorText = useErrorText();

  const problems: string[] = [];
  if (role === 'worker' && (skills.length < 1 || skills.length > 5)) problems.push(t('auth.skillsRequired'));
  if (role === 'worker' && !adult) problems.push(t('auth.ageRequired'));
  if (role === 'client' && !country.trim()) problems.push(t('auth.countryRequired'));
  const ready = name.trim() && email.includes('@') && password.length >= 8 && consent && problems.length === 0;

  const submit = () =>
    register.mutate(
      {
        role, email: email.trim(), password, display_name: name.trim(), locale, consent,
        ...(role === 'worker' ? { skills, age_attested: adult } : { country: country.trim(), org_label: org.trim() || null }),
      },
      { onSuccess: () => router.replace('/') },
    );

  return (
    <Screen title={t('auth.signUpTitle')} back>
      <Section title={t('auth.iAm')}>
        <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
          <Chip label={t('auth.asWorker')} on={role === 'worker'} onToggle={() => setRole('worker')} />
          <Chip label={t('auth.asClient')} on={role === 'client'} onToggle={() => setRole('client')} />
        </View>
      </Section>
      <Panel>
        <Field label={t('auth.displayName')} value={name} onChangeText={setName}
               help={role === 'worker' ? t('auth.displayNameHelpWorker') : t('auth.displayNameHelpClient')} />
        <Field label={t('auth.email')} value={email} onChangeText={setEmail} autoCapitalize="none"
               keyboardType="email-address" help={t('auth.emailHelp')} />
        <Field label={t('auth.password')} value={password} onChangeText={setPassword} secureTextEntry help={t('auth.passwordHelp')} />
        {role === 'client' ? (
          <>
            <Field label={t('auth.country')} value={country} onChangeText={setCountry} />
            <Field label={`${t('auth.orgLabel')} (${t('common.optional')})`} value={org} onChangeText={setOrg} />
          </>
        ) : (
          <Section title={t('auth.skills')}>
            <View style={{ flexDirection: 'row', gap: space.sm, flexWrap: 'wrap' }}>
              {(allSkills.data ?? []).map((s) => (
                <Chip key={s.id} label={pick(s.ne, s.en)} on={skills.includes(s.id)}
                      onToggle={() => setSkills((cur) => (cur.includes(s.id) ? cur.filter((x) => x !== s.id) : [...cur, s.id]))} />
              ))}
            </View>
          </Section>
        )}
      </Panel>
      <Panel tone="clay">
        <Section title={t('consent.title')}>
          <Bullet>{t('consent.email')}</Bullet>
          <Bullet>{t('consent.name')}</Bullet>
          {role === 'worker' ? <Bullet>{t('consent.skills')}</Bullet> : null}
          <Txt variant="small" color={colors.inkSoft}>{t('consent.never')}</Txt>
        </Section>
        {role === 'worker' ? <Checkbox label={t('auth.ageAttest')} checked={adult} onChange={setAdult} /> : null}
        <Checkbox label={t('auth.consentCheck')} checked={consent} onChange={setConsent} />
      </Panel>
      {register.isError ? (
        <Txt color={colors.brick}>{errorText(register.error, { '409': t('auth.emailTaken') })}</Txt>
      ) : null}
      <Button label={t('auth.signUp')} busy={register.isPending} disabled={!ready} onPress={submit} />
    </Screen>
  );
}
