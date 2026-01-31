import type { Metadata } from "next";
import { Breadcrumb } from "@/app/components/Breadcrumb";
import { StickyAd, StaticAd } from "@/app/components/Ads";
import motdData from "@/public/json/motd.json";
import Link from "next/link";
import { api } from "@/convex/_generated/api";
import { fetchQuery } from "convex/nextjs";
import { headers } from 'next/headers';
import { getCurrentUser } from '@/lib/auth';
import "@/app/narrow.css";

export const metadata: Metadata = {
  title: "Home - MyBusTimes",
  description: "Welcome to MyBusTimes",
};

export default async function Home() {
  const breadcrumbs = [{ label: "Home", href: "/" }];

  const randomMessage =
    motdData.messages[Math.floor(Math.random() * motdData.messages.length)];

  const regions = await fetchQuery(api.regions.getAllRegions);

  const topLevelRegions = regions.filter((r) => !r.parentId);
  const childRegions = regions.filter((r) => r.parentId);

  const regionGroups = topLevelRegions.map((parent) => ({
    parent,
    children: childRegions.filter((child) => child.parentId === parent._id),
  }));

  const headersList = await headers();
  const cookieHeader = headersList.get('cookie') || '';
  const user = await getCurrentUser(cookieHeader);
  
  const isAdmin = user?.isSuperuser || false;
  const isStaff = user?.isStaff || false;
  
  return (
    <>
      <Breadcrumb items={breadcrumbs} />
      <h2>Search</h2>
      <p>Search for operators or routes</p>
      <div className="homeSearch">
        <form action="search">
          <input type="search" name="q" id="q" placeholder="Search" />
          <input type="submit" value="Search" />
        </form>
      </div>
      <p>
        Note: MyBusTimes is 100% fictional. All data shown here is user
        generated and not real world data <Link href="/about">more info.</Link>
      </p>

      <StickyAd />

      <h2>Message of The Day</h2>
      <p>{randomMessage}</p>

      <div className="quick-links">
        <h2>Quick Links</h2>
        
        <div className="link-categories">
          <div className="link-category">
            <h3>Create</h3>
            <ul className="chips">
              <li className="chip"><Link href="/operator/create/">Company</Link></li>
              <li className="chip"><Link href="/create/livery">Livery</Link></li>
              <li className="chip"><Link href="/create/vehicle">Vehicle Type</Link></li>
            </ul>
          </div>

          <div className="link-category">
            <h3>Community</h3>
            <ul className="chips">
              <li className="chip"><Link href="/forum/">Forums</Link></li>
              <li className="chip"><Link href="/wiki/">Wiki</Link></li>
              <li className="chip">
                <Link href="/for_sale/">For Sale</Link>
                <span className="dot-badge" id="for-sale-count">403</span>
              </li>
            </ul>
          </div>

          <div className="link-category">
            <h3>Support</h3>
            <ul className="chips">
              <li className="chip"><Link href="/report">Report Bug</Link></li>
              <li className="chip"><Link href="/tickets/">Open Ticket</Link></li>
            </ul>
          </div>

          {(isStaff || isAdmin) && (
            <div className="link-category">
              <h3>Admin</h3>
              <ul className="chips">
                {isStaff && (
                  <li className="chip"><Link href="/staff/">Staff Portal</Link></li>
                )}
                {isAdmin && (
                  <li className="chip"><Link href="/admin/">Admin Portal</Link></li>
                )}
              </ul>
            </div>
          )}
        </div>
      </div>
      <StaticAd />

      <div id="regions-container">
        {regionGroups.map(({ parent, children }) => (
          <div key={parent._id}>
            <h2>{parent.name}</h2>
            <ul>
              {/* Show parent first */}
              <li>
                <Link href={`/region/${parent.code}`}>{parent.name}</Link>
              </li>
              {/* Then show children */}
              {children.map((region) => (
                <li key={region._id}>
                  <Link href={`/region/${region.code}`}>{region.name}</Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </>
  );
}
