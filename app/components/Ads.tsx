export function StickyAd() {
  return (
    <div className="top-ad-container in-page-ad ad" style={{marginBottom:"20px"}}>
      <div id="AFM_top_ad" className="top-ad-border" style={{margin:"auto"}}></div>
    </div>
  );
}

export function StaticAd() {
  return (
    <div className="incontent-ad-container in-page-ad ad" style={{height:"100px", marginBottom:"20px"}}>
      <div id="AFM_inContent_ad" style={{margin:"auto"}}></div>
    </div>
  );
}