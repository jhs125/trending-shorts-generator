import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import re

# ================== PAGE CONFIG ==================

st.set_page_config(
    page_title="Trending Shorts Idea Generator Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== CUSTOM CSS ==================

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .viral-badge {
        background: #ff4757;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .success-badge {
        background: #2ed573;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: transparent;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ================== CONSTANTS ==================

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

REGION_CODES = {
    "🌍 Global (US)": "US",
    "🇬🇧 United Kingdom": "GB",
    "🇨🇦 Canada": "CA",
    "🇦🇺 Australia": "AU",
    "🇮🇳 India": "IN",
    "🇩🇪 Germany": "DE",
    "🇫🇷 France": "FR",
    "🇧🇷 Brazil": "BR",
    "🇯🇵 Japan": "JP",
    "🇲🇽 Mexico": "MX",
}

NICHE_KEYWORDS = {
    "Motivation & Self Improvement": [
        "motivation shorts",
        "success motivation story",
        "self improvement tips",
        "discipline motivation",
        "morning routine motivation",
        "mindset shift",
    ],
    "Wealth & Money Stories": [
        "wealth stories",
        "money lessons shorts",
        "rich vs poor mindset",
        "finance motivation",
        "millionaire habits",
        "passive income ideas",
    ],
    "Scary / Dark Stories": [
        "scary story shorts",
        "true horror story",
        "dark stories real",
        "creepy real stories",
        "paranormal shorts",
        "horror facts",
    ],
    "Reddit / Drama Stories": [
        "reddit aita story",
        "reddit relationship story",
        "reddit drama shorts",
        "reddit storytime",
        "reddit revenge story",
        "reddit update",
    ],
    "Facts & Mind-Blowing Info": [
        "mind blowing facts",
        "crazy facts shorts",
        "top 10 facts",
        "did you know facts",
        "psychology facts",
        "interesting facts",
    ],
    "Space / Science Stories": [
        "space facts shorts",
        "science facts shorts",
        "cosmic stories",
        "universe facts",
        "astronomy shorts",
        "physics explained",
    ],
    "Health & Productivity": [
        "health tips shorts",
        "productivity hacks",
        "habit building shorts",
        "sleep tips shorts",
        "workout motivation",
        "nutrition facts",
    ],
    "History & Historical Facts": [
        "history facts shorts",
        "historical events",
        "ancient history",
        "war stories shorts",
        "historical figures",
    ],
    "Gaming & Tech": [
        "gaming shorts",
        "tech facts",
        "game tips shorts",
        "tech news shorts",
        "gaming moments",
    ],
    "Animals & Nature": [
        "animal facts shorts",
        "nature documentary shorts",
        "wildlife facts",
        "ocean facts",
        "pet videos shorts",
    ],
}

# ================== API KEY MANAGEMENT ==================

def get_api_key() -> Optional[str]:
    """
    Retrieve API key from multiple sources (priority order):
    1. Streamlit secrets
    2. Session state (user input)
    3. Environment variable
    """
    # Try Streamlit secrets first
    try:
        return st.secrets["YOUTUBE_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass
    
    # Try session state
    if "api_key" in st.session_state and st.session_state.api_key:
        return st.session_state.api_key
    
    return None

# ================== CACHING DECORATORS ==================

@st.cache_data(ttl=3600, show_spinner=False)
def cached_search_shorts(keyword: str, start_date: str, region: str, api_key: str, max_results: int = 15) -> Dict:
    """Cached YouTube search to save API quota."""
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "order": "viewCount",
        "publishedAfter": start_date,
        "maxResults": max_results,
        "videoDuration": "short",
        "regionCode": region,
        "key": api_key,
    }
    try:
        response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600, show_spinner=False)
def cached_video_details(video_ids_tuple: Tuple[str, ...], api_key: str) -> Dict:
    """Cached video details fetch."""
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids_tuple),
        "key": api_key,
    }
    try:
        response = requests.get(YOUTUBE_VIDEO_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600, show_spinner=False)
def cached_channel_stats(channel_ids_tuple: Tuple[str, ...], api_key: str) -> Dict:
    """Cached channel stats fetch."""
    params = {
        "part": "statistics,snippet",
        "id": ",".join(channel_ids_tuple),
        "key": api_key,
    }
    try:
        response = requests.get(YOUTUBE_CHANNEL_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# ================== HELPER FUNCTIONS ==================

def parse_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration to MM:SS format."""
    if not iso_duration or not iso_duration.startswith("PT"):
        return "00:00"
    
    duration = iso_duration[2:]  # Remove 'PT'
    minutes = 0
    seconds = 0
    
    # Extract minutes
    if "M" in duration:
        match = re.match(r'(\d+)M', duration)
        if match:
            minutes = int(match.group(1))
        duration = re.sub(r'\d+M', '', duration)
    
    # Extract seconds
    if "S" in duration:
        match = re.match(r'(\d+)S', duration)
        if match:
            seconds = int(match.group(1))
    
    return f"{minutes:02d}:{seconds:02d}"

def parse_duration_seconds(iso_duration: str) -> int:
    """Convert ISO 8601 duration to total seconds."""
    if not iso_duration or not iso_duration.startswith("PT"):
        return 0
    
    duration = iso_duration[2:]
    minutes = 0
    seconds = 0
    
    if "M" in duration:
        match = re.match(r'(\d+)M', duration)
        if match:
            minutes = int(match.group(1))
        duration = re.sub(r'\d+M', '', duration)
    
    if "S" in duration:
        match = re.match(r'(\d+)S', duration)
        if match:
            seconds = int(match.group(1))
    
    return minutes * 60 + seconds

def calculate_engagement_rate(views: int, likes: int, comments: int) -> float:
    """Calculate engagement rate as percentage."""
    if views == 0:
        return 0.0
    engagement = ((likes or 0) + (comments or 0)) / views * 100
    return round(engagement, 2)

def calculate_virality_score(views: int, subs: int, days_old: int) -> float:
    """
    Calculate virality score (0-100) based on:
    - Views to subscriber ratio
    - Views per day
    """
    if subs == 0 or days_old == 0:
        return 0.0
    
    views_per_sub = views / max(subs, 1)
    views_per_day = views / max(days_old, 1)
    
    # Normalize scores
    sub_ratio_score = min(views_per_sub * 10, 50)  # Max 50 points
    velocity_score = min(views_per_day / 1000 * 50, 50)  # Max 50 points
    
    return round(sub_ratio_score + velocity_score, 1)

def calculate_days_old(published_at: str) -> int:
    """Calculate days since video was published."""
    try:
        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        now = datetime.now(pub_date.tzinfo)
        return (now - pub_date).days
    except:
        return 0

def generate_idea_angle(title: str, niche: str, views: int, engagement: float) -> str:
    """Generate actionable idea angle based on video performance."""
    hooks = []
    
    if views > 1000000:
        hooks.append("VIRAL format")
    elif views > 100000:
        hooks.append("High-performing format")
    
    if engagement > 5:
        hooks.append("high engagement hook")
    
    hook_text = ", ".join(hooks) if hooks else "trending format"
    
    return (
        f"Recreate this {hook_text} for '{niche}'. "
        f"Study: '{title[:50]}...' - Adapt the hook structure, "
        f"change the examples, maintain similar pacing."
    )

def format_number(num: int) -> str:
    """Format large numbers for display (1.2M, 500K, etc.)."""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

def get_virality_label(score: float) -> str:
    """Get virality tier label."""
    if score >= 80:
        return "🔥 VIRAL"
    elif score >= 60:
        return "⚡ Hot"
    elif score >= 40:
        return "📈 Growing"
    elif score >= 20:
        return "✅ Good"
    return "📊 Normal"

def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")

def convert_df_to_excel(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes."""
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Shorts Ideas')
    return output.getvalue()

# ================== SIDEBAR ==================

with st.sidebar:
    st.title("⚙️ Settings")
    
    # API Key Section
    st.markdown("### 🔑 API Configuration")
    
    api_key = get_api_key()
    
    if not api_key:
        st.warning("No API key found in secrets")
        user_key = st.text_input(
            "Enter YouTube API Key:",
            type="password",
            help="Get your key from Google Cloud Console"
        )
        if user_key:
            st.session_state.api_key = user_key
            api_key = user_key
            st.success("✅ API key set for this session")
    else:
        st.success("✅ API key configured")
        if st.button("🔄 Change API Key"):
            st.session_state.api_key = ""
            st.rerun()
    
    st.markdown("---")
    
    # Search Filters
    st.markdown("### 🎯 Search Filters")
    
    days = st.slider(
        "Days to search back:",
        min_value=1,
        max_value=30,
        value=7,
        help="Search for videos published within this timeframe"
    )
    
    region = st.selectbox(
        "Target Region:",
        options=list(REGION_CODES.keys()),
        index=0,
        help="Filter results by geographic region"
    )
    
    results_per_keyword = st.select_slider(
        "Results per keyword:",
        options=[5, 10, 15, 20, 25],
        value=10,
        help="More results = more API quota used"
    )
    
    st.markdown("---")
    
    # Performance Filters
    st.markdown("### 📊 Performance Filters")
    
    min_views = st.number_input(
        "Minimum views:",
        min_value=0,
        value=5000,
        step=1000,
        help="Only show videos with at least this many views"
    )
    
    max_subs = st.number_input(
        "Maximum channel subs:",
        min_value=0,
        value=50000,
        step=5000,
        help="Find small channels with viral content (0 = no limit)"
    )
    
    min_engagement = st.slider(
        "Minimum engagement rate (%):",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.5,
        help="Engagement = (likes + comments) / views × 100"
    )
    
    min_virality = st.slider(
        "Minimum virality score:",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        help="Combined score based on views/subs ratio and growth velocity"
    )
    
    st.markdown("---")
    
    # Duration Filter
    st.markdown("### ⏱️ Duration Filter")
    
    duration_range = st.slider(
        "Video duration (seconds):",
        min_value=0,
        max_value=60,
        value=(0, 60),
        help="Filter Shorts by duration"
    )
    
    st.markdown("---")
    
    # Info Section
    st.markdown("### 💡 Pro Tips")
    st.info(
        "**Finding viral opportunities:**\n"
        "• Low subs + High views = Viral content\n"
        "• High engagement = Strong hooks\n"
        "• High virality score = Replicable"
    )

# ================== MAIN CONTENT ==================

st.title("📈 Trending Shorts Idea Generator Pro")
st.markdown(
    "Find **viral YouTube Shorts** from **small channels**, analyze their performance, "
    "and get actionable ideas for your own content."
)

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["🔍 Search", "📊 Analytics", "ℹ️ How To Use"])

with tab1:
    # Niche Selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        niche = st.selectbox(
            "🎯 Choose your niche:",
            list(NICHE_KEYWORDS.keys()),
            help="Each niche has optimized search keywords"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        show_keywords = st.checkbox("Show keywords", value=False)
    
    if show_keywords:
        st.caption(f"**Keywords for {niche}:** {', '.join(NICHE_KEYWORDS[niche])}")
    
    # Custom Keywords
    with st.expander("➕ Add Custom Keywords (Optional)"):
        custom_keywords = st.text_area(
            "Enter additional keywords (one per line):",
            placeholder="motivational stories\nsuccess tips\nmindset shorts",
            height=100
        )
    
    # Search Button
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_btn = st.button(
            "🚀 Find Trending Shorts",
            type="primary",
            use_container_width=True,
            disabled=not api_key
        )

    # ================== SEARCH EXECUTION ==================
    
    if search_btn:
        if not api_key:
            st.error("❌ Please configure your YouTube API key in the sidebar")
        else:
            # Prepare keywords
            keywords = NICHE_KEYWORDS.get(niche, []).copy()
            if custom_keywords:
                custom_list = [kw.strip() for kw in custom_keywords.split('\n') if kw.strip()]
                keywords.extend(custom_list)
            
            # Calculate date range
            start_date = (datetime.utcnow() - timedelta(days=int(days))).isoformat("T") + "Z"
            region_code = REGION_CODES[region]
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_rows = []
            seen_video_ids = set()  # Prevent duplicates
            errors = []
            
            for idx, kw in enumerate(keywords):
                progress = (idx + 1) / len(keywords)
                progress_bar.progress(progress)
                status_text.text(f"🔎 Searching: {kw} ({idx + 1}/{len(keywords)})")
                
                # Search for videos
                search_data = cached_search_shorts(kw, start_date, region_code, api_key, results_per_keyword)
                
                if "error" in search_data:
                    errors.append(f"Search error for '{kw}': {search_data['error']}")
                    continue
                
                if "items" not in search_data or not search_data["items"]:
                    continue
                
                videos = search_data["items"]
                video_ids = [v["id"]["videoId"] for v in videos if v["id"]["videoId"] not in seen_video_ids]
                channel_ids = list(set([v["snippet"]["channelId"] for v in videos]))
                
                if not video_ids:
                    continue
                
                # Mark as seen
                seen_video_ids.update(video_ids)
                
                # Fetch detailed data
                vid_details = cached_video_details(tuple(video_ids), api_key)
                chan_details = cached_channel_stats(tuple(channel_ids), api_key)
                
                if "error" in vid_details or "error" in chan_details:
                    continue
                
                # Build lookup maps
                vid_map = {item["id"]: item for item in vid_details.get("items", [])}
                chan_map = {item["id"]: item for item in chan_details.get("items", [])}
                
                # Process each video
                for v in videos:
                    vid_id = v["id"]["videoId"]
                    ch_id = v["snippet"]["channelId"]
                    
                    if vid_id not in vid_map:
                        continue
                    
                    v_detail = vid_map.get(vid_id, {})
                    c_detail = chan_map.get(ch_id, {})
                    
                    v_snippet = v_detail.get("snippet", {})
                    v_stats = v_detail.get("statistics", {})
                    v_content = v_detail.get("contentDetails", {})
                    c_stats = c_detail.get("statistics", {})
                    c_snippet = c_detail.get("snippet", {})
                    
                    # Extract metrics
                    views = int(v_stats.get("viewCount", 0))
                    likes = int(v_stats.get("likeCount", 0)) if "likeCount" in v_stats else 0
                    comments = int(v_stats.get("commentCount", 0)) if "commentCount" in v_stats else 0
                    subs = int(c_stats.get("subscriberCount", 0)) if "subscriberCount" in c_stats else 0
                    
                    # Duration check
                    duration_sec = parse_duration_seconds(v_content.get("duration", ""))
                    if duration_sec < duration_range[0] or duration_sec > duration_range[1]:
                        continue
                    
                    # Calculate derived metrics
                    published_at = v_snippet.get("publishedAt", "")
                    days_old = calculate_days_old(published_at)
                    engagement_rate = calculate_engagement_rate(views, likes, comments)
                    virality_score = calculate_virality_score(views, subs, max(days_old, 1))
                    views_per_day = views / max(days_old, 1)
                    
                    # Apply filters
                    if views < min_views:
                        continue
                    if max_subs > 0 and subs > max_subs:
                        continue
                    if engagement_rate < min_engagement:
                        continue
                    if virality_score < min_virality:
                        continue
                    
                    # Build row
                    title = v_snippet.get("title", "")
                    description = v_snippet.get("description", "")
                    tags = v_snippet.get("tags", [])
                    thumbnails = v_snippet.get("thumbnails", {})
                    
                    all_rows.append({
                        # Identifiers
                        "Video ID": vid_id,
                        "Video Title": title,
                        "Video URL": f"https://youtube.com/shorts/{vid_id}",
                        
                        # Performance
                        "Views": views,
                        "Likes": likes,
                        "Comments": comments,
                        "Engagement Rate (%)": engagement_rate,
                        "Virality Score": virality_score,
                        "Virality Tier": get_virality_label(virality_score),
                        "Views/Day": round(views_per_day, 0),
                        
                        # Video Details
                        "Duration": parse_duration(v_content.get("duration", "")),
                        "Duration (sec)": duration_sec,
                        "Published": published_at[:10] if published_at else "",
                        "Days Old": days_old,
                        "Description": description[:300],
                        "Tags": ", ".join(tags[:10]) if tags else "",
                        
                        # Thumbnails
                        "Thumbnail": thumbnails.get("high", {}).get("url", thumbnails.get("default", {}).get("url", "")),
                        
                        # Channel
                        "Channel": v_snippet.get("channelTitle", ""),
                        "Channel URL": f"https://youtube.com/channel/{ch_id}",
                        "Channel Subs": subs,
                        "Channel Country": c_snippet.get("country", "N/A"),
                        
                        # Meta
                        "Niche": niche,
                        "Keyword": kw,
                        "Region": region,
                        
                        # Actionable
                        "Idea Angle": generate_idea_angle(title, niche, views, engagement_rate),
                    })
                
                # Rate limiting protection
                time.sleep(0.1)
            
            progress_bar.empty()
            status_text.empty()
            
            # Show errors if any
            if errors:
                with st.expander(f"⚠️ {len(errors)} warnings occurred"):
                    for err in errors:
                        st.warning(err)
            
            # Process and display results
            if all_rows:
                results_df = pd.DataFrame(all_rows)
                results_df = results_df.sort_values(
                    by=["Virality Score", "Views"],
                    ascending=[False, False]
                ).reset_index(drop=True)
                
                # Store in session state
                st.session_state.results_df = results_df
                st.session_state.search_completed = True
                
                # Summary Metrics
                st.markdown("---")
                st.subheader("📊 Search Results Summary")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Videos Found", len(results_df))
                with col2:
                    st.metric("Avg Views", format_number(int(results_df["Views"].mean())))
                with col3:
                    st.metric("Avg Engagement", f"{results_df['Engagement Rate (%)'].mean():.2f}%")
                with col4:
                    viral_count = len(results_df[results_df["Virality Score"] >= 60])
                    st.metric("Viral Videos", viral_count)
                with col5:
                    st.metric("Avg Virality", f"{results_df['Virality Score'].mean():.1f}")
                
                # Results Table
                st.markdown("---")
                st.subheader("🎬 Video Results")
                
                # Display options
                display_cols = st.multiselect(
                    "Columns to display:",
                    options=results_df.columns.tolist(),
                    default=[
                        "Video Title", "Views", "Engagement Rate (%)", 
                        "Virality Tier", "Channel", "Channel Subs", "Video URL"
                    ]
                )
                
                if display_cols:
                    st.dataframe(
                        results_df[display_cols],
                        use_container_width=True,
                        height=400,
                        column_config={
                            "Video URL": st.column_config.LinkColumn("Video URL"),
                            "Channel URL": st.column_config.LinkColumn("Channel URL"),
                            "Thumbnail": st.column_config.ImageColumn("Thumbnail", width="medium"),
                            "Views": st.column_config.NumberColumn("Views", format="%d"),
                            "Virality Score": st.column_config.ProgressColumn(
                                "Virality Score",
                                min_value=0,
                                max_value=100,
                            ),
                        }
                    )
                
                # Download Options
                st.markdown("---")
                st.subheader("📥 Export Results")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.download_button(
                        "📄 Download CSV",
                        data=convert_df_to_csv(results_df),
                        file_name=f"shorts_ideas_{niche.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    try:
                        excel_data = convert_df_to_excel(results_df)
                        st.download_button(
                            "📊 Download Excel",
                            data=excel_data,
                            file_name=f"shorts_ideas_{niche.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.info("Install openpyxl for Excel export")
                
                with col3:
                    st.download_button(
                        "📋 Download JSON",
                        data=results_df.to_json(orient="records", indent=2),
                        file_name=f"shorts_ideas_{niche.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            
            else:
                st.warning(
                    "No videos matched your filters. Try:\n"
                    "- Increasing days to search\n"
                    "- Lowering minimum views\n"
                    "- Increasing max channel subscribers\n"
                    "- Lowering engagement/virality minimums"
                )

with tab2:
    st.subheader("📊 Analytics Dashboard")
    
    if "results_df" in st.session_state and not st.session_state.results_df.empty:
        df = st.session_state.results_df
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Views Distribution")
            st.bar_chart(df.nsmallest(20, 'Channel Subs').set_index('Video Title')['Views'])
        
        with col2:
            st.markdown("#### Virality Score Distribution")
            virality_dist = df['Virality Tier'].value_counts()
            st.bar_chart(virality_dist)
        
        st.markdown("---")
        
        # Top Performers
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏆 Top 5 by Virality")
            top_viral = df.nlargest(5, 'Virality Score')[['Video Title', 'Views', 'Virality Score', 'Channel']]
            st.dataframe(top_viral, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 💬 Top 5 by Engagement")
            top_engage = df.nlargest(5, 'Engagement Rate (%)')[['Video Title', 'Views', 'Engagement Rate (%)', 'Channel']]
            st.dataframe(top_engage, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Keyword Performance
        st.markdown("#### 🔍 Keyword Performance")
        keyword_stats = df.groupby('Keyword').agg({
            'Views': 'mean',
            'Virality Score': 'mean',
            'Video ID': 'count'
        }).rename(columns={'Video ID': 'Videos Found'}).round(1)
        st.dataframe(keyword_stats.sort_values('Virality Score', ascending=False), use_container_width=True)
        
    else:
        st.info("Run a search first to see analytics!")

with tab3:
    st.subheader("📖 How To Use This Tool")
    
    st.markdown("""
    ### 🎯 Finding Viral Short Ideas
    
    1. **Select a Niche** - Choose from pre-built categories or add custom keywords
    2. **Adjust Filters** - Use sidebar filters to narrow down results
    3. **Analyze Results** - Look for high virality scores with low subscriber counts
    4. **Export & Execute** - Download ideas and create your own versions
    
    ---
    
    ### 📊 Understanding Metrics
    
    | Metric | What It Means | Good Value |
    |--------|---------------|------------|
    | **Virality Score** | Combined measure of performance relative to channel size | 60+ = Viral |
    | **Engagement Rate** | (Likes + Comments) / Views × 100 | 3%+ = Good |
    | **Views/Day** | Average views per day since publish | 10K+ = Trending |
    
    ---
    
    ### 💰 Monetization Ideas
    
    - **Faceless Channels**: Create your own content based on trending ideas
    - **Sell Idea Lists**: Offer weekly curated lists to content creators
    - **YouTube Automation**: Provide full-service content creation
    - **Coaching**: Teach others how to find and replicate viral content
    
    ---
    
    ### 🔑 Getting Your API Key
    
    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
    2. Create a new project
    3. Enable **YouTube Data API v3**
    4. Create credentials → API Key
    5. Add key to Streamlit secrets or paste in sidebar
    
    ---
    
    ### 🔒 Storing API Key Securely
    
    For deployment, create `.streamlit/secrets.toml`:
    ```toml
    YOUTUBE_API_KEY = "your-api-key-here"
    ```
    """)

# ================== FOOTER ==================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>Built with ❤️ for content creators | 
        <a href='https://developers.google.com/youtube/v3' target='_blank'>YouTube API Docs</a></p>
    </div>
    """,
    unsafe_allow_html=True
)
