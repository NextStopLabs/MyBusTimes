'use client'

type BanMessageProps = {
  banned: { reason: string; type: string } | null;
  fullPage?: boolean;
};

export function BanMessage({ banned, fullPage = false }: BanMessageProps) {
  if (!banned) return null;

  return (
    <div className={fullPage ? 'ban-message-page' : ''}>
      <div className="ban-message-card">
        <h2>Account banned</h2>
        <p className="ban-reason">
          <strong>Reason:</strong> {banned.reason}
        </p>
        <p className="ban-type">Ban type: {banned.type}</p>
      </div>
    </div>
  );
}
