"""
USGS Earthquake API Tools

Provides tools to query earthquake data from the USGS Earthquake Hazards Program.
Designed for skill mode scenarios with large geospatial output data.

API Documentation: https://earthquake.usgs.gov/fdsnws/event/1/
No authentication required.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests
from datetime import datetime, timedelta

# Base URL for USGS Earthquake API
USGS_BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1"


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to the USGS API with error handling."""
    url = f"{USGS_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timeout", "success": False}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}


def _parse_params(params_str: str) -> dict:
    """Parse parameters from string."""
    if not params_str:
        return {}
    if isinstance(params_str, dict):
        return params_str
    try:
        return json.loads(params_str)
    except json.JSONDecodeError:
        return {}


# ============== Tool Implementation Functions ==============

def _query_earthquakes_by_region(latitude: float, longitude: float, 
                                  radius_km: int = 500, 
                                  min_magnitude: float = 2.5,
                                  days_back: int = 30) -> dict:
    """Query earthquakes near a specific location with VERBOSE full earthquake data for skill mode."""
    
    # Calculate date range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days_back)
    
    # MODERATE VERBOSE: Balanced data volume
    params = {
        "format": "geojson",
        "latitude": latitude,
        "longitude": longitude,
        "maxradiuskm": radius_km,
        "minmagnitude": min_magnitude,
        "starttime": start_time.strftime("%Y-%m-%d"),
        "endtime": end_time.strftime("%Y-%m-%d"),
        "orderby": "magnitude",
        "limit": 200  # MODERATE: Reduced from 1000 to avoid context explosion
    }
    
    data = _make_request("/query", params)
    
    if "error" in data:
        return data
    
    features = data.get("features", [])
    
    # Process earthquakes - VERBOSE: Include ALL fields from API
    earthquakes = []
    magnitude_distribution = {
        "2.5-3.9": 0,
        "4.0-4.9": 0,
        "5.0-5.9": 0,
        "6.0-6.9": 0,
        "7.0+": 0
    }
    
    # VERBOSE: Detailed breakdown by depth
    depth_breakdown = {
        "shallow_0_20km": [],
        "crustal_20_70km": [],
        "intermediate_70_300km": [],
        "deep_300km_plus": []
    }
    
    # VERBOSE: Breakdown by time
    daily_breakdown = {}
    hourly_counts = {f"{h:02d}:00": 0 for h in range(24)}
    
    max_earthquake = None
    max_magnitude = 0
    total_depth = 0
    depth_count = 0
    felt_events = []
    tsunami_events = []
    
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0, 0])
        
        mag = props.get("mag", 0) or 0
        depth = coords[2] if len(coords) > 2 else None
        time_ms = props.get("time")
        
        # VERBOSE: Include ALL available properties
        eq = {
            "id": feature.get("id"),
            "magnitude": mag,
            "magnitude_type": props.get("magType"),
            "place": props.get("place"),
            "time": time_ms,
            "time_formatted": datetime.fromtimestamp(time_ms / 1000).strftime("%Y-%m-%d %H:%M:%S UTC") if time_ms else None,
            "updated": props.get("updated"),
            "updated_formatted": datetime.fromtimestamp(props.get("updated", 0) / 1000).strftime("%Y-%m-%d %H:%M:%S UTC") if props.get("updated") else None,
            "depth_km": round(depth, 2) if depth else None,
            "latitude": round(coords[1], 4) if len(coords) > 1 else None,
            "longitude": round(coords[0], 4) if len(coords) > 0 else None,
            "horizontal_error_km": props.get("horizontalError"),
            "depth_error_km": props.get("depthError"),
            "magnitude_error": props.get("magError"),
            "magnitude_nst": props.get("magNst"),
            "felt": props.get("felt"),
            "cdi": props.get("cdi"),  # Community Decimal Intensity
            "mmi": props.get("mmi"),  # Modified Mercalli Intensity
            "alert": props.get("alert"),
            "tsunami": props.get("tsunami"),
            "significance": props.get("sig"),
            "net": props.get("net"),  # Network
            "code": props.get("code"),
            "ids": props.get("ids"),
            "sources": props.get("sources"),
            "types": props.get("types"),
            "nst": props.get("nst"),  # Number of stations
            "dmin": props.get("dmin"),  # Distance to nearest station
            "rms": props.get("rms"),  # Root mean square residual
            "gap": props.get("gap"),  # Azimuthal gap
            "status": props.get("status"),
            "type": props.get("type"),
            "title": props.get("title"),
            "detail_url": props.get("detail"),
            "url": props.get("url")
        }
        earthquakes.append(eq)
        
        # Track maximum
        if mag > max_magnitude:
            max_magnitude = mag
            max_earthquake = eq
        
        # Categorize by magnitude
        if 2.5 <= mag < 4.0:
            magnitude_distribution["2.5-3.9"] += 1
        elif 4.0 <= mag < 5.0:
            magnitude_distribution["4.0-4.9"] += 1
        elif 5.0 <= mag < 6.0:
            magnitude_distribution["5.0-5.9"] += 1
        elif 6.0 <= mag < 7.0:
            magnitude_distribution["6.0-6.9"] += 1
        elif mag >= 7.0:
            magnitude_distribution["7.0+"] += 1
        
        # VERBOSE: Categorize by depth
        if depth is not None:
            total_depth += depth
            depth_count += 1
            eq_summary = {"id": eq["id"], "magnitude": mag, "depth_km": round(depth, 1), "place": eq["place"][:60] if eq["place"] else None}
            if depth < 20:
                depth_breakdown["shallow_0_20km"].append(eq_summary)
            elif depth < 70:
                depth_breakdown["crustal_20_70km"].append(eq_summary)
            elif depth < 300:
                depth_breakdown["intermediate_70_300km"].append(eq_summary)
            else:
                depth_breakdown["deep_300km_plus"].append(eq_summary)
        
        # VERBOSE: Track daily and hourly distribution
        if time_ms:
            dt = datetime.fromtimestamp(time_ms / 1000)
            day_key = dt.strftime("%Y-%m-%d")
            if day_key not in daily_breakdown:
                daily_breakdown[day_key] = {"count": 0, "max_magnitude": 0, "events": []}
            daily_breakdown[day_key]["count"] += 1
            daily_breakdown[day_key]["max_magnitude"] = max(daily_breakdown[day_key]["max_magnitude"], mag)
            if len(daily_breakdown[day_key]["events"]) < 5:  # Keep top 5 per day
                daily_breakdown[day_key]["events"].append({"magnitude": mag, "place": eq["place"][:40] if eq["place"] else None})
            hourly_counts[f"{dt.hour:02d}:00"] += 1
        
        # Track felt and tsunami events
        if props.get("felt") and props.get("felt") > 0:
            felt_events.append({"id": eq["id"], "magnitude": mag, "felt_count": props.get("felt"), "place": eq["place"]})
        if props.get("tsunami") == 1:
            tsunami_events.append({"id": eq["id"], "magnitude": mag, "place": eq["place"]})
    
    # Calculate statistics
    daily_average = len(earthquakes) / days_back if days_back > 0 else 0
    avg_depth = total_depth / depth_count if depth_count > 0 else None
    
    # Determine risk level
    if max_magnitude >= 6.0 or len(earthquakes) > 100:
        risk_level = "High"
        risk_factors = []
        if max_magnitude >= 6.0:
            risk_factors.append(f"M{max_magnitude:.1f} earthquake recorded")
        if len(earthquakes) > 100:
            risk_factors.append(f"High frequency: {len(earthquakes)} events in {days_back} days")
    elif max_magnitude >= 5.0 or len(earthquakes) > 50:
        risk_level = "Moderate"
        risk_factors = ["Moderate seismic activity"]
    elif max_magnitude >= 4.0 or len(earthquakes) > 20:
        risk_level = "Low"
        risk_factors = ["Low seismic activity"]
    else:
        risk_level = "Minimal"
        risk_factors = ["Minimal seismic activity"]
    
    return {
        "success": True,
        "query": {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "min_magnitude": min_magnitude,
            "days_back": days_back,
            "date_range": {
                "start": start_time.strftime("%Y-%m-%d"),
                "end": end_time.strftime("%Y-%m-%d")
            }
        },
        "results": {
            "total_count": len(earthquakes),
            "magnitude_distribution": magnitude_distribution,
            "max_magnitude": max_magnitude,
            "max_earthquake": max_earthquake,
            "daily_average": round(daily_average, 2),
            "average_depth_km": round(avg_depth, 1) if avg_depth else None,
            "risk_level": risk_level,
            "risk_factors": risk_factors
        },
        # VERBOSE: Detailed breakdown for pattern to extract summary from
        "depth_analysis": {
            "shallow_0_20km": {"count": len(depth_breakdown["shallow_0_20km"]), "events": depth_breakdown["shallow_0_20km"][:20]},
            "crustal_20_70km": {"count": len(depth_breakdown["crustal_20_70km"]), "events": depth_breakdown["crustal_20_70km"][:20]},
            "intermediate_70_300km": {"count": len(depth_breakdown["intermediate_70_300km"]), "events": depth_breakdown["intermediate_70_300km"][:20]},
            "deep_300km_plus": {"count": len(depth_breakdown["deep_300km_plus"]), "events": depth_breakdown["deep_300km_plus"][:20]}
        },
        "temporal_analysis": {
            "daily_breakdown": daily_breakdown,
            "hourly_distribution": hourly_counts,
            "peak_hour": max(hourly_counts.keys(), key=lambda k: hourly_counts[k]) if hourly_counts else None,
            "most_active_day": max(daily_breakdown.keys(), key=lambda k: daily_breakdown[k]["count"]) if daily_breakdown else None
        },
        "special_events": {
            "felt_earthquakes": felt_events[:30],
            "tsunami_warnings": tsunami_events,
            "high_significance": [eq for eq in earthquakes if eq.get("significance", 0) and eq.get("significance", 0) > 500][:20]
        },
        # ULTRA VERBOSE: Additional analysis data
        "magnitude_statistics": {
            "mean": round(sum(eq.get("magnitude", 0) or 0 for eq in earthquakes) / len(earthquakes), 2) if earthquakes else 0,
            "max": max((eq.get("magnitude", 0) or 0 for eq in earthquakes), default=0),
            "min": min((eq.get("magnitude", 0) or 0 for eq in earthquakes if eq.get("magnitude")), default=0),
            "by_type": {
                "ml": len([eq for eq in earthquakes if eq.get("magnitude_type") == "ml"]),
                "mb": len([eq for eq in earthquakes if eq.get("magnitude_type") == "mb"]),
                "mw": len([eq for eq in earthquakes if eq.get("magnitude_type") == "mw"]),
                "md": len([eq for eq in earthquakes if eq.get("magnitude_type") == "md"]),
                "other": len([eq for eq in earthquakes if eq.get("magnitude_type") not in ["ml", "mb", "mw", "md"]])
            }
        },
        "network_coverage": {
            "networks": list(set(eq.get("net") for eq in earthquakes if eq.get("net"))),
            "station_counts": {
                "avg_stations": round(sum(eq.get("nst", 0) or 0 for eq in earthquakes) / len(earthquakes), 1) if earthquakes else 0,
                "max_stations": max((eq.get("nst", 0) or 0 for eq in earthquakes), default=0)
            }
        },
        "quality_metrics": {
            "avg_gap": round(sum(eq.get("gap", 0) or 0 for eq in earthquakes) / len(earthquakes), 1) if earthquakes else 0,
            "avg_rms": round(sum(eq.get("rms", 0) or 0 for eq in earthquakes) / len(earthquakes), 3) if earthquakes else 0,
            "reviewed_count": len([eq for eq in earthquakes if eq.get("status") == "reviewed"]),
            "automatic_count": len([eq for eq in earthquakes if eq.get("status") == "automatic"])
        },
        # ULTRA VERBOSE: FULL earthquake list for pattern to process
        "earthquakes": earthquakes
    }


def _get_recent_significant(min_magnitude: float = 5.0, days_back: int = 7) -> dict:
    """Get recent significant earthquakes worldwide."""
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days_back)
    
    params = {
        "format": "geojson",
        "minmagnitude": min_magnitude,
        "starttime": start_time.strftime("%Y-%m-%d"),
        "endtime": end_time.strftime("%Y-%m-%d"),
        "orderby": "magnitude"
    }
    
    data = _make_request("/query", params)
    
    if "error" in data:
        return data
    
    features = data.get("features", [])
    
    earthquakes = []
    regions = {}
    
    for feature in features[:30]:  # Limit to 30 most significant
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0, 0])
        
        place = props.get("place", "Unknown")
        region = place.split(",")[-1].strip() if "," in place else place
        
        eq = {
            "id": feature.get("id"),
            "magnitude": props.get("mag"),
            "place": place,
            "region": region,
            "time_formatted": datetime.fromtimestamp(props.get("time", 0) / 1000).strftime("%Y-%m-%d %H:%M:%S") if props.get("time") else None,
            "depth_km": coords[2] if len(coords) > 2 else None,
            "latitude": coords[1],
            "longitude": coords[0],
            "alert": props.get("alert"),
            "tsunami": props.get("tsunami")
        }
        earthquakes.append(eq)
        
        # Track by region
        if region not in regions:
            regions[region] = {"count": 0, "max_mag": 0}
        regions[region]["count"] += 1
        regions[region]["max_mag"] = max(regions[region]["max_mag"], props.get("mag", 0) or 0)
    
    # Sort regions by count
    top_regions = sorted(regions.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    
    return {
        "success": True,
        "query": {
            "min_magnitude": min_magnitude,
            "days_back": days_back,
            "date_range": {
                "start": start_time.strftime("%Y-%m-%d"),
                "end": end_time.strftime("%Y-%m-%d")
            }
        },
        "results": {
            "total_count": len(features),
            "returned_count": len(earthquakes),
            "top_regions": [{"region": r, "count": d["count"], "max_magnitude": d["max_mag"]} for r, d in top_regions]
        },
        "earthquakes": earthquakes
    }


# ============== NEW: Region Statistics Tool ==============

def _get_region_stats(latitude: float, longitude: float, radius_km: int = 500) -> dict:
    """Get detailed statistical analysis for a region based on 30-day data."""
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)
    
    params = {
        "format": "geojson",
        "latitude": latitude,
        "longitude": longitude,
        "maxradiuskm": radius_km,
        "minmagnitude": 1.0,
        "starttime": start_time.strftime("%Y-%m-%d"),
        "endtime": end_time.strftime("%Y-%m-%d"),
        "orderby": "time"
    }
    
    data = _make_request("/query", params)
    
    if "error" in data:
        return data
    
    features = data.get("features", [])
    
    if not features:
        return {
            "success": True,
            "message": "No earthquakes found in this region",
            "statistics": None
        }
    
    magnitudes = []
    depths = []
    times = []
    
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0, 0])
        
        mag = props.get("mag")
        if mag is not None:
            magnitudes.append(mag)
        
        depth = coords[2] if len(coords) > 2 else None
        if depth is not None:
            depths.append(depth)
        
        time_ms = props.get("time")
        if time_ms:
            times.append(time_ms)
    
    # Calculate statistics
    if magnitudes:
        avg_mag = sum(magnitudes) / len(magnitudes)
        sorted_mags = sorted(magnitudes)
        median_mag = sorted_mags[len(sorted_mags) // 2]
        std_dev = (sum((m - avg_mag) ** 2 for m in magnitudes) / len(magnitudes)) ** 0.5
        
        # Percentiles
        p10_idx = int(len(sorted_mags) * 0.1)
        p25_idx = int(len(sorted_mags) * 0.25)
        p75_idx = int(len(sorted_mags) * 0.75)
        p90_idx = int(len(sorted_mags) * 0.9)
        
        magnitude_stats = {
            "count": len(magnitudes),
            "min": min(magnitudes),
            "max": max(magnitudes),
            "mean": round(avg_mag, 2),
            "median": round(median_mag, 2),
            "std_deviation": round(std_dev, 3),
            "percentiles": {
                "p10": round(sorted_mags[p10_idx], 2),
                "p25": round(sorted_mags[p25_idx], 2),
                "p75": round(sorted_mags[p75_idx], 2),
                "p90": round(sorted_mags[p90_idx], 2)
            }
        }
    else:
        magnitude_stats = None
    
    if depths:
        avg_depth = sum(depths) / len(depths)
        depth_stats = {
            "count": len(depths),
            "min_km": round(min(depths), 1),
            "max_km": round(max(depths), 1),
            "mean_km": round(avg_depth, 1),
            "shallow_count": sum(1 for d in depths if d < 70),
            "intermediate_count": sum(1 for d in depths if 70 <= d < 300),
            "deep_count": sum(1 for d in depths if d >= 300)
        }
    else:
        depth_stats = None
    
    # Time distribution (earthquakes per day of week)
    if times:
        day_counts = {i: 0 for i in range(7)}  # 0=Monday, 6=Sunday
        hour_counts = {i: 0 for i in range(24)}
        
        for t in times:
            dt = datetime.fromtimestamp(t / 1000)
            day_counts[dt.weekday()] += 1
            hour_counts[dt.hour] += 1
        
        time_distribution = {
            "by_day_of_week": {
                "Monday": day_counts[0],
                "Tuesday": day_counts[1],
                "Wednesday": day_counts[2],
                "Thursday": day_counts[3],
                "Friday": day_counts[4],
                "Saturday": day_counts[5],
                "Sunday": day_counts[6]
            },
            "by_hour": {f"{h:02d}:00": hour_counts[h] for h in range(24)},
            "peak_hour": max(hour_counts.keys(), key=lambda k: hour_counts[k]),
            "peak_day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
                max(day_counts.keys(), key=lambda k: day_counts[k])
            ]
        }
    else:
        time_distribution = None
    
    return {
        "success": True,
        "query": {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "period_days": 30
        },
        "statistics": {
            "total_earthquakes": len(features),
            "magnitude": magnitude_stats,
            "depth": depth_stats,
            "time_distribution": time_distribution,
            "daily_rate": round(len(features) / 30, 2),
            "weekly_rate": round(len(features) / 4.3, 2)
        }
    }


# ============== NEW: Historical Trends Tool ==============

def _get_historical_trends(latitude: float, longitude: float, radius_km: int = 500) -> dict:
    """Get 90-day historical earthquake trends with month-over-month comparison."""
    
    end_time = datetime.utcnow()
    
    # Get data for 3 months
    monthly_data = []
    
    for month_offset in range(3):
        month_end = end_time - timedelta(days=30 * month_offset)
        month_start = month_end - timedelta(days=30)
        
        params = {
            "format": "geojson",
            "latitude": latitude,
            "longitude": longitude,
            "maxradiuskm": radius_km,
            "minmagnitude": 2.5,
            "starttime": month_start.strftime("%Y-%m-%d"),
            "endtime": month_end.strftime("%Y-%m-%d")
        }
        
        data = _make_request("/query", params)
        
        if "error" in data:
            continue
        
        features = data.get("features", [])
        magnitudes = [f.get("properties", {}).get("mag", 0) or 0 for f in features]
        
        monthly_data.append({
            "month": month_start.strftime("%Y-%m"),
            "period": {
                "start": month_start.strftime("%Y-%m-%d"),
                "end": month_end.strftime("%Y-%m-%d")
            },
            "count": len(features),
            "max_magnitude": max(magnitudes) if magnitudes else 0,
            "avg_magnitude": round(sum(magnitudes) / len(magnitudes), 2) if magnitudes else 0,
            "m4_plus_count": sum(1 for m in magnitudes if m >= 4.0),
            "m5_plus_count": sum(1 for m in magnitudes if m >= 5.0)
        })
    
    # Calculate trends
    if len(monthly_data) >= 2:
        current = monthly_data[0]["count"]
        previous = monthly_data[1]["count"]
        change = current - previous
        change_pct = (change / previous * 100) if previous > 0 else 0
        
        if change_pct > 20:
            trend = "increasing_significant"
        elif change_pct > 5:
            trend = "increasing_slight"
        elif change_pct < -20:
            trend = "decreasing_significant"
        elif change_pct < -5:
            trend = "decreasing_slight"
        else:
            trend = "stable"
        
        # Anomaly detection
        if len(monthly_data) >= 3:
            avg_count = sum(m["count"] for m in monthly_data[1:]) / 2
            if current > avg_count * 1.5:
                anomaly = "elevated_activity"
            elif current < avg_count * 0.5:
                anomaly = "reduced_activity"
            else:
                anomaly = "normal"
        else:
            anomaly = "insufficient_data"
    else:
        trend = "insufficient_data"
        change_pct = 0
        anomaly = "insufficient_data"
    
    return {
        "success": True,
        "query": {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "total_period_days": 90
        },
        "trends": {
            "direction": trend,
            "month_over_month_change_percent": round(change_pct, 1) if len(monthly_data) >= 2 else None,
            "anomaly_status": anomaly,
            "recommendation": "Monitor closely" if trend.startswith("increasing") else "Normal monitoring"
        },
        "monthly_breakdown": monthly_data,
        "summary": {
            "total_90_day_count": sum(m["count"] for m in monthly_data),
            "average_monthly_count": round(sum(m["count"] for m in monthly_data) / len(monthly_data), 1) if monthly_data else 0,
            "max_magnitude_90_days": max(m["max_magnitude"] for m in monthly_data) if monthly_data else 0,
            "total_m5_plus": sum(m["m5_plus_count"] for m in monthly_data)
        }
    }


# ============== NEW: Depth Analysis Tool ==============

def _get_depth_analysis(latitude: float, longitude: float, radius_km: int = 500) -> dict:
    """Get earthquake depth distribution analysis for a region."""
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)
    
    params = {
        "format": "geojson",
        "latitude": latitude,
        "longitude": longitude,
        "maxradiuskm": radius_km,
        "minmagnitude": 1.0,
        "starttime": start_time.strftime("%Y-%m-%d"),
        "endtime": end_time.strftime("%Y-%m-%d")
    }
    
    data = _make_request("/query", params)
    
    if "error" in data:
        return data
    
    features = data.get("features", [])
    
    # Depth categories (in km)
    depth_categories = {
        "crustal_shallow": {"range": "0-20 km", "count": 0, "earthquakes": []},
        "crustal_deep": {"range": "20-70 km", "count": 0, "earthquakes": []},
        "intermediate": {"range": "70-300 km", "count": 0, "earthquakes": []},
        "deep": {"range": "300+ km", "count": 0, "earthquakes": []}
    }
    
    depth_magnitude_correlation = []
    
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0, 0])
        
        depth = coords[2] if len(coords) > 2 else None
        mag = props.get("mag", 0) or 0
        
        if depth is None:
            continue
        
        eq_summary = {
            "magnitude": mag,
            "depth_km": round(depth, 1),
            "place": props.get("place", "Unknown")[:50]
        }
        
        depth_magnitude_correlation.append({"depth": depth, "magnitude": mag})
        
        if depth < 20:
            depth_categories["crustal_shallow"]["count"] += 1
            if len(depth_categories["crustal_shallow"]["earthquakes"]) < 5:
                depth_categories["crustal_shallow"]["earthquakes"].append(eq_summary)
        elif depth < 70:
            depth_categories["crustal_deep"]["count"] += 1
            if len(depth_categories["crustal_deep"]["earthquakes"]) < 5:
                depth_categories["crustal_deep"]["earthquakes"].append(eq_summary)
        elif depth < 300:
            depth_categories["intermediate"]["count"] += 1
            if len(depth_categories["intermediate"]["earthquakes"]) < 5:
                depth_categories["intermediate"]["earthquakes"].append(eq_summary)
        else:
            depth_categories["deep"]["count"] += 1
            if len(depth_categories["deep"]["earthquakes"]) < 5:
                depth_categories["deep"]["earthquakes"].append(eq_summary)
    
    # Determine dominant depth type
    total = sum(cat["count"] for cat in depth_categories.values())
    if total > 0:
        dominant_category = max(depth_categories.keys(), key=lambda k: depth_categories[k]["count"])
        dominant_pct = depth_categories[dominant_category]["count"] / total * 100
    else:
        dominant_category = "none"
        dominant_pct = 0
    
    # Calculate depth-magnitude correlation
    if len(depth_magnitude_correlation) >= 5:
        depths = [d["depth"] for d in depth_magnitude_correlation]
        mags = [d["magnitude"] for d in depth_magnitude_correlation]
        
        avg_depth = sum(depths) / len(depths)
        avg_mag = sum(mags) / len(mags)
        
        # Simple correlation coefficient
        numerator = sum((d - avg_depth) * (m - avg_mag) for d, m in zip(depths, mags))
        denom_depth = sum((d - avg_depth) ** 2 for d in depths) ** 0.5
        denom_mag = sum((m - avg_mag) ** 2 for m in mags) ** 0.5
        
        if denom_depth > 0 and denom_mag > 0:
            correlation = numerator / (denom_depth * denom_mag)
        else:
            correlation = 0
        
        correlation_analysis = {
            "coefficient": round(correlation, 3),
            "interpretation": "positive" if correlation > 0.3 else "negative" if correlation < -0.3 else "weak",
            "note": "Positive means deeper earthquakes tend to be stronger" if correlation > 0.3 else "No strong correlation" if abs(correlation) <= 0.3 else "Deeper earthquakes tend to be weaker"
        }
    else:
        correlation_analysis = {"coefficient": None, "note": "Insufficient data"}
    
    return {
        "success": True,
        "query": {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "period_days": 30
        },
        "depth_analysis": {
            "total_earthquakes": total,
            "categories": depth_categories,
            "dominant_type": {
                "category": dominant_category,
                "percentage": round(dominant_pct, 1),
                "description": {
                    "crustal_shallow": "Shallow crustal earthquakes - typically felt more strongly at surface",
                    "crustal_deep": "Deep crustal earthquakes - moderate surface impact",
                    "intermediate": "Intermediate depth - subduction zone activity",
                    "deep": "Deep earthquakes - subducting slab activity"
                }.get(dominant_category, "Unknown")
            },
            "depth_magnitude_correlation": correlation_analysis,
            "seismic_zone_type": "subduction" if depth_categories["intermediate"]["count"] + depth_categories["deep"]["count"] > total * 0.3 else "crustal"
        }
    }


# ============== NEW: Tectonic Info Tool ==============

def _get_tectonic_info(latitude: float, longitude: float) -> dict:
    """Get tectonic plate boundary information for a region (simulated based on known plate boundaries)."""
    
    # Known major plate boundaries (simplified)
    plate_boundaries = [
        {"name": "Pacific-North American (San Andreas)", "type": "transform", "lat": 37.0, "lon": -122.0, "region": "California"},
        {"name": "Pacific-Philippine", "type": "subduction", "lat": 35.0, "lon": 140.0, "region": "Japan"},
        {"name": "Indo-Australian-Eurasian", "type": "subduction", "lat": -6.0, "lon": 107.0, "region": "Indonesia"},
        {"name": "Nazca-South American", "type": "subduction", "lat": -33.0, "lon": -72.0, "region": "Chile"},
        {"name": "North Anatolian Fault", "type": "transform", "lat": 41.0, "lon": 29.0, "region": "Turkey"},
        {"name": "Pacific-Australian", "type": "subduction", "lat": -41.0, "lon": 175.0, "region": "New Zealand"},
        {"name": "Mid-Atlantic Ridge", "type": "divergent", "lat": 35.0, "lon": -35.0, "region": "Atlantic Ocean"},
        {"name": "East African Rift", "type": "divergent", "lat": -2.0, "lon": 36.0, "region": "East Africa"},
    ]
    
    # Find nearest plate boundary
    def distance(lat1, lon1, lat2, lon2):
        return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5
    
    nearest = min(plate_boundaries, key=lambda b: distance(latitude, longitude, b["lat"], b["lon"]))
    dist = distance(latitude, longitude, nearest["lat"], nearest["lon"])
    
    # Get all boundaries within reasonable distance
    nearby_boundaries = [b for b in plate_boundaries if distance(latitude, longitude, b["lat"], b["lon"]) < 30]
    
    # Determine hazard level based on boundary type and distance
    boundary_type = nearest["type"]
    if dist < 5:
        proximity = "very_close"
        if boundary_type == "subduction":
            hazard_level = "very_high"
            hazard_note = "Region is directly on a subduction zone - high risk of large earthquakes and tsunamis"
        elif boundary_type == "transform":
            hazard_level = "high"
            hazard_note = "Region is on a transform fault - high risk of strike-slip earthquakes"
        else:
            hazard_level = "moderate"
            hazard_note = "Region is on a divergent boundary - moderate seismic risk"
    elif dist < 15:
        proximity = "close"
        hazard_level = "high" if boundary_type == "subduction" else "moderate"
        hazard_note = f"Region is near a {boundary_type} plate boundary"
    elif dist < 30:
        proximity = "moderate"
        hazard_level = "moderate"
        hazard_note = "Region is within the plate boundary zone"
    else:
        proximity = "distant"
        hazard_level = "low"
        hazard_note = "Region is distant from major plate boundaries"
    
    # Expected earthquake characteristics based on boundary type
    expected_characteristics = {
        "subduction": {
            "typical_depths": "0-700 km",
            "max_magnitude_potential": "9.0+",
            "tsunami_risk": "high",
            "typical_mechanisms": ["thrust", "normal"],
            "notable_hazards": ["megathrust earthquakes", "tsunami generation", "volcanic activity"]
        },
        "transform": {
            "typical_depths": "0-20 km",
            "max_magnitude_potential": "8.0",
            "tsunami_risk": "low",
            "typical_mechanisms": ["strike-slip"],
            "notable_hazards": ["surface rupture", "ground shaking", "liquefaction"]
        },
        "divergent": {
            "typical_depths": "0-30 km",
            "max_magnitude_potential": "7.0",
            "tsunami_risk": "low",
            "typical_mechanisms": ["normal"],
            "notable_hazards": ["volcanic activity", "rift formation"]
        }
    }
    
    return {
        "success": True,
        "query": {
            "location": {"latitude": latitude, "longitude": longitude}
        },
        "tectonic_setting": {
            "nearest_boundary": {
                "name": nearest["name"],
                "type": nearest["type"],
                "region": nearest["region"],
                "approximate_distance_degrees": round(dist, 1),
                "proximity": proximity
            },
            "nearby_boundaries": [
                {"name": b["name"], "type": b["type"], "distance_degrees": round(distance(latitude, longitude, b["lat"], b["lon"]), 1)}
                for b in nearby_boundaries[:3]
            ],
            "boundary_type_description": {
                "subduction": "One tectonic plate diving beneath another",
                "transform": "Two plates sliding horizontally past each other",
                "divergent": "Two plates moving apart from each other"
            }.get(boundary_type, "Unknown")
        },
        "hazard_assessment": {
            "overall_level": hazard_level,
            "note": hazard_note,
            "expected_characteristics": expected_characteristics.get(boundary_type, {}),
            "historical_context": f"This region ({nearest['region']}) is known for significant seismic activity"
        },
        "recommendations": {
            "monitoring_priority": "high" if hazard_level in ["high", "very_high"] else "standard",
            "preparedness_level": hazard_level,
            "key_risks": expected_characteristics.get(boundary_type, {}).get("notable_hazards", [])
        }
    }


# ============== Tool Handlers ==============

async def on_query_earthquakes_by_region(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for querying earthquakes by region."""
    params = _parse_params(params_str)
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    
    if latitude is None or longitude is None:
        return {"error": "latitude and longitude are required", "success": False}
    
    radius_km = params.get("radius_km", 500)
    min_magnitude = params.get("min_magnitude", 2.5)
    days_back = params.get("days_back", 30)
    
    result = _query_earthquakes_by_region(
        float(latitude), 
        float(longitude), 
        int(radius_km), 
        float(min_magnitude), 
        int(days_back)
    )
    return result


async def on_get_recent_significant(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting recent significant earthquakes."""
    params = _parse_params(params_str)
    
    min_magnitude = params.get("min_magnitude", 5.0)
    days_back = params.get("days_back", 7)
    
    result = _get_recent_significant(float(min_magnitude), int(days_back))
    return result


async def on_get_region_stats(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting region statistics."""
    params = _parse_params(params_str)
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    
    if latitude is None or longitude is None:
        return {"error": "latitude and longitude are required", "success": False}
    
    radius_km = params.get("radius_km", 500)
    result = _get_region_stats(float(latitude), float(longitude), int(radius_km))
    return result


async def on_get_historical_trends(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting historical trends."""
    params = _parse_params(params_str)
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    
    if latitude is None or longitude is None:
        return {"error": "latitude and longitude are required", "success": False}
    
    radius_km = params.get("radius_km", 500)
    result = _get_historical_trends(float(latitude), float(longitude), int(radius_km))
    return result


async def on_get_depth_analysis(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting depth analysis."""
    params = _parse_params(params_str)
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    
    if latitude is None or longitude is None:
        return {"error": "latitude and longitude are required", "success": False}
    
    radius_km = params.get("radius_km", 500)
    result = _get_depth_analysis(float(latitude), float(longitude), int(radius_km))
    return result


async def on_get_tectonic_info(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting tectonic info."""
    params = _parse_params(params_str)
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    
    if latitude is None or longitude is None:
        return {"error": "latitude and longitude are required", "success": False}
    
    result = _get_tectonic_info(float(latitude), float(longitude))
    return result


# ============== Tool Definitions ==============

tool_usgs_query_earthquakes = FunctionTool(
    name='local-usgs_query_earthquakes',
    description='''Query earthquakes near a specific location within a radius.

**Returns:** dict:
{
  "success": bool,
  "query": {
    "center": {"latitude": float, "longitude": float},
    "radius_km": int,
    "min_magnitude": float,
    "days_back": int,
    "date_range": {"start": str, "end": str}
  },
  "results": {
    "total_count": int,
    "magnitude_distribution": {"2.5-3.9": int, "4.0-4.9": int, "5.0-5.9": int, "6.0-6.9": int, "7.0+": int},
    "max_magnitude": float,
    "max_earthquake": {...},
    "daily_average": float,
    "risk_level": str
  },
  "earthquakes": [
    {
      "id": str,
      "magnitude": float,
      "place": str,
      "time": int,
      "time_formatted": str,
      "depth_km": float,
      "latitude": float,
      "longitude": float,
      "felt": int | null,
      "alert": str | null,
      "tsunami": int,
      "significance": int,
      "type": str
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude of the center point"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the center point"
            },
            "radius_km": {
                "type": "integer",
                "description": "Search radius in kilometers (default: 500)"
            },
            "min_magnitude": {
                "type": "number",
                "description": "Minimum earthquake magnitude to include (default: 2.5)"
            },
            "days_back": {
                "type": "integer",
                "description": "Number of days to look back (default: 30)"
            }
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_query_earthquakes_by_region
)

tool_usgs_recent_significant = FunctionTool(
    name='local-usgs_recent_significant',
    description='''Get recent significant earthquakes worldwide.

**Returns:** dict:
{
  "success": bool,
  "query": {
    "min_magnitude": float,
    "days_back": int,
    "date_range": {"start": str, "end": str}
  },
  "results": {
    "total_count": int,
    "returned_count": int,
    "top_regions": [{"region": str, "count": int, "max_magnitude": float}]
  },
  "earthquakes": [
    {
      "id": str,
      "magnitude": float,
      "place": str,
      "region": str,
      "time_formatted": str,
      "depth_km": float,
      "latitude": float,
      "longitude": float,
      "alert": str | null,
      "tsunami": int
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "min_magnitude": {
                "type": "number",
                "description": "Minimum magnitude threshold (default: 5.0)"
            },
            "days_back": {
                "type": "integer",
                "description": "Number of days to look back (default: 7)"
            }
        }
    },
    on_invoke_tool=on_get_recent_significant
)

tool_usgs_get_region_stats = FunctionTool(
    name='local-usgs_get_region_stats',
    description='''Get detailed statistical analysis for a seismic region.

**Returns:** dict:
{
  "success": bool,
  "query": {
    "center": {"latitude": float, "longitude": float},
    "radius_km": int,
    "period_days": int
  },
  "statistics": {
    "total_earthquakes": int,
    "magnitude": {
      "count": int, "min": float, "max": float, "mean": float, "median": float, "std_deviation": float,
      "percentiles": {"p10": float, "p25": float, "p75": float, "p90": float}
    },
    "depth": {
      "count": int, "min_km": float, "max_km": float, "mean_km": float,
      "shallow_count": int, "intermediate_count": int, "deep_count": int
    },
    "time_distribution": {
      "by_day_of_week": {"Monday": int, "Tuesday": int, ...},
      "by_hour": {"00:00": int, "01:00": int, ...},
      "peak_hour": int,
      "peak_day": str
    },
    "daily_rate": float,
    "weekly_rate": float
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude of the center point"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the center point"
            },
            "radius_km": {
                "type": "integer",
                "description": "Search radius in kilometers (default: 500)"
            }
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_get_region_stats
)

tool_usgs_get_historical_trends = FunctionTool(
    name='local-usgs_get_historical_trends',
    description='''Get 90-day historical earthquake trends with month-over-month comparison.

**Returns:** dict:
{
  "success": bool,
  "query": {
    "center": {"latitude": float, "longitude": float},
    "radius_km": int,
    "total_period_days": int
  },
  "trends": {
    "direction": str,
    "month_over_month_change_percent": float | null,
    "anomaly_status": str,
    "recommendation": str
  },
  "monthly_breakdown": [
    {
      "month": str,
      "period": {"start": str, "end": str},
      "count": int,
      "max_magnitude": float,
      "avg_magnitude": float,
      "m4_plus_count": int,
      "m5_plus_count": int
    }
  ],
  "summary": {
    "total_90_day_count": int,
    "average_monthly_count": float,
    "max_magnitude_90_days": float,
    "total_m5_plus": int
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude of the center point"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the center point"
            },
            "radius_km": {
                "type": "integer",
                "description": "Search radius in kilometers (default: 500)"
            }
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_get_historical_trends
)

tool_usgs_get_depth_analysis = FunctionTool(
    name='local-usgs_get_depth_analysis',
    description='''Get earthquake depth distribution analysis for a region.

**Returns:** dict:
{
  "success": bool,
  "query": {
    "center": {"latitude": float, "longitude": float},
    "radius_km": int,
    "period_days": int
  },
  "depth_analysis": {
    "total_earthquakes": int,
    "categories": {
      "crustal_shallow": {"range": str, "count": int, "earthquakes": [{"magnitude": float, "depth_km": float, "place": str}]},
      "crustal_deep": {"range": str, "count": int, "earthquakes": [...]},
      "intermediate": {"range": str, "count": int, "earthquakes": [...]},
      "deep": {"range": str, "count": int, "earthquakes": [...]}
    },
    "dominant_type": {
      "category": str,
      "percentage": float,
      "description": str
    },
    "depth_magnitude_correlation": {
      "coefficient": float | null,
      "interpretation": str,
      "note": str
    },
    "seismic_zone_type": str
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude of the center point"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the center point"
            },
            "radius_km": {
                "type": "integer",
                "description": "Search radius in kilometers (default: 500)"
            }
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_get_depth_analysis
)

tool_usgs_get_tectonic_info = FunctionTool(
    name='local-usgs_get_tectonic_info',
    description='''Get tectonic plate boundary information for a region.

**Returns:** dict:
{
  "success": bool,
  "query": {"location": {"latitude": float, "longitude": float}},
  "tectonic_setting": {
    "nearest_boundary": {
      "name": str,
      "type": str,
      "region": str,
      "approximate_distance_degrees": float,
      "proximity": str
    },
    "nearby_boundaries": [{"name": str, "type": str, "distance_degrees": float}],
    "boundary_type_description": str
  },
  "hazard_assessment": {
    "overall_level": str,
    "note": str,
    "expected_characteristics": {
      "typical_depths": str,
      "max_magnitude_potential": str,
      "tsunami_risk": str,
      "typical_mechanisms": [str],
      "notable_hazards": [str]
    },
    "historical_context": str
  },
  "recommendations": {
    "monitoring_priority": str,
    "preparedness_level": str,
    "key_risks": [str]
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude of the location"
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the location"
            }
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_get_tectonic_info
)


# Export all tools as a list
usgs_earthquake_tools = [
    tool_usgs_query_earthquakes,
    tool_usgs_get_region_stats,
    tool_usgs_get_historical_trends,
    tool_usgs_get_depth_analysis,
    tool_usgs_get_tectonic_info,
]

