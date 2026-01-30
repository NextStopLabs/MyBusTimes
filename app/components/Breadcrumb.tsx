import Link from "next/link";

type BreadcrumbItem = {
  label: string;
  href: string;
};

type BreadcrumbProps = {
  items: BreadcrumbItem[];
};

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <div className="breadcrumb">
      <ol>
        {items.map((item, index) => (
          <li key={`${item.href}+${item.label}`} className="default">
            {index > 0 && <span className="separator">&nbsp;</span>}
            {index === items.length - 1 ? (
              <span className="current">{item.label}&nbsp;</span>
            ) : (
              <Link href={item.href}>{item.label}</Link>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
