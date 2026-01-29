import type { Metadata } from "next";
import { Breadcrumb } from '@/app/components/Breadcrumb';
import { StickyAd } from '@/app/components/Ads';
import motdData from '@/public/json/motd.json';
import Link from 'next/link';
import "./narrow.css";

export const metadata: Metadata = {
  title: "Home - MyBusTimes",
  description: "Welcome to MyBusTimes",
};

export default function Home() {
  const breadcrumbs = [
    { label: 'Home', href: '/' },
  ];
  
  const randomMessage = motdData.messages[Math.floor(Math.random() * motdData.messages.length)];

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
      <p>Note: MyBusTimes is 100% fictional. All data shown here is user generated and not real world data <Link href="/about">more info.</Link></p>
      <StickyAd />
      <h2>Message of The Day</h2>
      <p>{randomMessage}</p>
    </>
  );
}