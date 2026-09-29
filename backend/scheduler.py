from apscheduler.schedulers.background import BackgroundScheduler

from concurrent.futures import ThreadPoolExecutor, as_completed

import threading

from datetime import datetime

from database import SessionLocal

from models import Competitor

from monitor import check_competitor


# =========================================================
# CONFIGURATION
# =========================================================

# Maximum number of competitors checked simultaneously
MAX_WORKERS = 10


# =========================================================
# SINGLE COMPETITOR WORKER
# =========================================================

def check_single_competitor(competitor_id):

    db = SessionLocal()

    try:

        competitor = (
            db.query(Competitor)
            .filter(
                Competitor.id == competitor_id
            )
            .first()
        )

        if not competitor:

            return {
                "competitor_id": competitor_id,
                "success": False,
                "new_articles": 0,
                "error": "Competitor not found"
            }

        print(
            f"Checking: {competitor.name}"
        )

        result = check_competitor(
            competitor,
            db
        )

        return {
            "competitor_id": competitor.id,

            "competitor": competitor.name,

            "success": result.get(
                "success",
                False
            ),

            "new_articles": result.get(
                "new_articles",
                0
            ),

            "error": result.get(
                "error"
            )
        }

    except Exception as e:

        print(
            f"Error checking competitor "
            f"{competitor_id}: {e}"
        )

        db.rollback()

        return {
            "competitor_id": competitor_id,
            "success": False,
            "new_articles": 0,
            "error": str(e)
        }

    finally:

        db.close()


# =========================================================
# MONITOR ALL COMPETITORS
# =========================================================

def monitor_all_competitors():

    db = SessionLocal()

    try:

        competitors = (
            db.query(Competitor)
            .filter(
                Competitor.monitoring_enabled == True
            )
            .all()
        )

        competitor_ids = [
            competitor.id
            for competitor in competitors
        ]

    finally:

        db.close()

    total = len(competitor_ids)

    print()

    print("=" * 60)

    print(
        f"[{datetime.now()}] "
        f"Checking {total} competitors"
    )

    print(
        f"Concurrent workers: {MAX_WORKERS}"
    )

    print("=" * 60)

    if total == 0:

        print(
            "No enabled competitors."
        )

        return

    # =====================================================
    # STATISTICS
    # =====================================================

    successful = 0

    failed = 0

    no_source = 0

    total_new_articles = 0

    # =====================================================
    # CONCURRENT WORKERS
    # =====================================================

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {
            executor.submit(
                check_single_competitor,
                competitor_id
            ): competitor_id

            for competitor_id in competitor_ids
        }

        for future in as_completed(futures):

            competitor_id = futures[future]

            try:

                result = future.result()

                competitor_name = result.get(
                    "competitor",
                    f"ID {competitor_id}"
                )

                new_articles = result.get(
                    "new_articles",
                    0
                )

                error = result.get(
                    "error"
                )

                # =========================================
                # SUCCESS
                # =========================================

                if result.get("success"):

                    successful += 1

                    print(
                        f"✓ {competitor_name}: "
                        f"{new_articles} new articles"
                    )

                # =========================================
                # NO SOURCE
                # =========================================

                elif (
                    error is not None
                    and error.strip().lower()
                    == (
                        "no rss, sitemap, or "
                        "blog source configured"
                    )
                ):

                    no_source += 1

                    print(
                        f"⚠ {competitor_name}: "
                        f"No monitoring source configured"
                    )

                # =========================================
                # ACTUAL FAILURE
                # =========================================

                else:

                    failed += 1

                    print(
                        f"✗ {competitor_name}: "
                        f"{error}"
                    )

                total_new_articles += new_articles

            except Exception as e:

                failed += 1

                print(
                    f"✗ Worker error for "
                    f"competitor {competitor_id}: "
                    f"{e}"
                )

    # =====================================================
    # CYCLE SUMMARY
    # =====================================================

    print()

    print(
        f"Monitoring cycle complete | "
        f"Total: {total} | "
        f"Successful: {successful} | "
        f"Failed: {failed} | "
        f"No Source: {no_source} | "
        f"New articles: {total_new_articles}"
    )

    print("=" * 60)

    print()


# =========================================================
# APSCHEDULER
# =========================================================

scheduler = BackgroundScheduler()


def _job_id(competitor_id: int) -> str:
    return f"monitor_competitor_{competitor_id}"


def schedule_competitor(competitor_id: int, interval_minutes: int):
    """Add or replace the per-competitor monitoring job."""
    job_id = _job_id(competitor_id)
    scheduler.add_job(
        check_single_competitor,
        "interval",
        minutes=max(1, interval_minutes),
        args=[competitor_id],
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30
    )
    print(
        f"Scheduled competitor {competitor_id} "
        f"every {interval_minutes} min (job: {job_id})"
    )


def unschedule_competitor(competitor_id: int):
    """Remove the per-competitor monitoring job if it exists."""
    job_id = _job_id(competitor_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"Removed job for competitor {competitor_id}")


def sync_competitor_schedules():
    """
    Called at startup and periodically to ensure every enabled
    competitor has a scheduled job with the correct interval, and
    that disabled / deleted competitors have their jobs removed.
    """
    db = SessionLocal()
    try:
        competitors = db.query(Competitor).all()
        active_ids = set()

        for comp in competitors:
            try:
                if comp.monitoring_enabled:
                    interval = getattr(comp, "check_interval_minutes", None) or 1
                    schedule_competitor(comp.id, interval)
                    active_ids.add(comp.id)
                else:
                    unschedule_competitor(comp.id)
            except Exception as ce:
                print(f"[sync] error scheduling competitor {comp.id}: {ce}")

        # Clean up jobs for competitors that no longer exist in DB
        for job in scheduler.get_jobs():
            if job.id.startswith("monitor_competitor_"):
                try:
                    cid = int(job.id.split("_")[-1])
                    if cid not in active_ids:
                        scheduler.remove_job(job.id)
                        print(f"Cleaned up stale job for competitor {cid}")
                except Exception:
                    pass

    except Exception as e:
        print(f"[sync] sync_competitor_schedules error: {e}")
        db.rollback()
    finally:
        db.close()



# Re-sync schedules every 2 minutes to pick up interval changes
scheduler.add_job(
    sync_competitor_schedules,
    "interval",
    minutes=2,
    id="sync_schedules",
    replace_existing=True,
    max_instances=1,
    coalesce=True,
    misfire_grace_time=30
)


# =========================================================
# START SCHEDULER
# =========================================================

def start_scheduler():

    if not scheduler.running:

        scheduler.start()

        print(
            "ContentPulse scheduler started."
        )

    # Defer initial sync to a background thread so startup_event
    # can complete even if the DB isn't ready yet or the column is missing.
    def _deferred_sync():
        import time
        time.sleep(3)  # give the DB connection pool a moment to settle
        try:
            sync_competitor_schedules()
        except Exception as e:
            print(f"[scheduler] initial sync failed (will retry in 2 min): {e}")

    threading.Thread(target=_deferred_sync, daemon=True).start()
