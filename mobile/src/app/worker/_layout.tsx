import { RoleTabs } from '@/components/RoleTabs';

export default function WorkerTabs() {
  return (
    <RoleTabs
      tabs={[
        { name: 'work', titleKey: 'tabs.myWork', icon: 'work' },
        { name: 'board', titleKey: 'tabs.board', icon: 'board' },
        { name: 'passport', titleKey: 'tabs.passport', icon: 'passport' },
        { name: 'inbox', titleKey: 'tabs.inbox', icon: 'inbox' },
        { name: 'help', titleKey: 'tabs.help', icon: 'help' },
      ]}
    />
  );
}
