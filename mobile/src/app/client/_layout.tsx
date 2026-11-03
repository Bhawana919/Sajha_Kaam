import { RoleTabs } from '@/components/RoleTabs';

export default function ClientTabs() {
  return (
    <RoleTabs
      tabs={[
        { name: 'post', titleKey: 'tabs.post', icon: 'post' },
        { name: 'cards', titleKey: 'tabs.myCards', icon: 'cards' },
        { name: 'review', titleKey: 'tabs.review', icon: 'review' },
        { name: 'inbox', titleKey: 'tabs.inbox', icon: 'inbox' },
        { name: 'help', titleKey: 'tabs.help', icon: 'help' },
      ]}
    />
  );
}
