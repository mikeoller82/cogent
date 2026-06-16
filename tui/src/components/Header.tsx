/** @jsxImportSource @opentui/react */
import { theme } from '../theme';

const COGENT_LOGO = [
  '╔═══╗╔═╗╔═╗╔═══╗╔═══╗╔╗──╔═══╗',
  '╚══╗║║║╚╝║║║╔═╗║║╔══╝║║──║╔══╝',
  '──╔╝║║║╔╗║║║╚═╝║║╚══╗║║──║╚══╗',
  '╚═╝─╚╝╚╝╚╝╚╝═══╝╚═══╝╚╝──╚═══╝',
];

export function Header() {
  return (
    <box
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        padding: { left: 1, right: 1 },
        borderStyle: 'single',
        borderColor: theme.border,
        backgroundColor: theme.surface,
        height: 7,
      }}
    >
      {/* Logo block */}
      <box
        style={{
          flexDirection: 'column',
          marginRight: 2,
        }}
      >
        {COGENT_LOGO.map((line, i) => (
          <text
            key={i}
            style={{
              color: theme.secondary,
            }}
            content={line}
          />
        ))}
      </box>

      {/* Title + subtitle */}
      <box
        style={{
          flexDirection: 'column',
          flexGrow: 1,
        }}
      >
      <text
        style={{
          color: theme.accent,
        }}
        content="COGENT"
      />
      <text
        style={{
          color: theme.textMuted,
        }}
        content="AI co-worker — terminal interface"
      />
      <text
        style={{
          color: theme.textDim,
        }}
        content="Plan · Execute · Verify"
      />
      </box>
    </box>
  );
}
