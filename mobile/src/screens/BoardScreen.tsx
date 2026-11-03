// Kaam Board: open cards with the Pahilo Kaam filter and bilingual search. Guests can browse.
import { router } from 'expo-router';
import { useState } from 'react';
import { FlatList, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { useBoard } from '@/api/hooks';
import { BoardItem } from '@/components/KaamCard';
import { FadeIn } from '@/components/motion';
import { LangSwitch, OfflineBanner } from '@/components/Screen';
import { Icon } from '@/components/Icon';
import { Txt } from '@/components/Txt';
import { Button, Chip, DemoBanner, StateView } from '@/components/ui';
import { useT } from '@/i18n';
import { border, colors, contentMaxWidth, radius, space, touchMin } from '@/theme';

export function BoardScreen() {
  const { t } = useT();
  const [pahilo, setPahilo] = useState(false);
  const [q, setQ] = useState('');
  const board = useBoard({ pahilo, q });

  const header = (
    <View style={{ gap: space.md, paddingBottom: space.md }}>
      <Txt color={colors.inkSoft}>{t('board.subtitle')}</Txt>
      <View style={{ justifyContent: 'center' }}>
      <View style={{ position: 'absolute', left: space.md }} pointerEvents="none">
        <Icon name="search" size={20} color={colors.inkSoft} />
      </View>
      <TextInput
        value={q}
        onChangeText={setQ}
        placeholder={t('board.searchPlaceholder')}
        placeholderTextColor={colors.inkSoft}
        accessibilityLabel={t('board.searchPlaceholder')}
        returnKeyType="search"
        style={{
          minHeight: touchMin,
          borderWidth: border,
          borderColor: colors.line,
          borderRadius: radius.md,
          backgroundColor: colors.white,
          paddingLeft: space.md + 28,
          paddingRight: space.md,
          fontSize: 15,
          color: colors.ink,
        }}
      />
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm, flexWrap: 'wrap' }}>
        <Chip label={t('board.pahiloFilter')} on={pahilo} onToggle={() => setPahilo((p) => !p)} />
        <Txt variant="small" color={colors.inkSoft} style={{ flex: 1, minWidth: 160 }}>{t('board.pahiloHelp')}</Txt>
      </View>
      <DemoBanner />
    </View>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.paper }} edges={['top']}>
      <View style={{ paddingHorizontal: space.lg, paddingVertical: space.sm, borderBottomWidth: border, borderBottomColor: colors.line }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', width: '100%', maxWidth: contentMaxWidth, alignSelf: 'center' }}>
          <Txt variant="h2" accessibilityRole="header" style={{ flex: 1 }}>{t('board.title')}</Txt>
          <LangSwitch />
        </View>
      </View>
      <OfflineBanner />
      <FlatList
        data={board.data?.items ?? []}
        keyExtractor={(c) => c.id}
        contentContainerStyle={{ padding: space.lg, gap: space.md, width: '100%', maxWidth: contentMaxWidth, alignSelf: 'center' }}
        ListHeaderComponent={header}
        renderItem={({ item, index }) => (
          <FadeIn delay={index * 45}>
            <BoardItem card={item} onPress={() => router.push({ pathname: '/card/[id]', params: { id: item.id } })} />
          </FadeIn>
        )}
        ListEmptyComponent={
          board.isPending ? (
            <StateView state="loading" />
          ) : board.isError ? (
            <StateView
              state="error"
              message={board.error instanceof ApiError && board.error.kind === 'network' ? t('errors.network') : undefined}
              onRetry={() => board.refetch()}
            />
          ) : (
            <StateView state="empty" message={t('board.empty')}
                       action={pahilo ? <Button kind="secondary" label={t('board.pahiloFilter')} icon="close" onPress={() => setPahilo(false)} /> : undefined} />
          )
        }
        initialNumToRender={6}
        windowSize={7}
        removeClippedSubviews
        refreshing={board.isRefetching}
        onRefresh={() => board.refetch()}
      />
    </SafeAreaView>
  );
}
