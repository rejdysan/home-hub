"""Google Calendar service for fetching events using Service Account."""
import asyncio
import socket
from datetime import datetime, timedelta
from typing import Dict
from pathlib import Path

import httplib2
from google.oauth2 import service_account
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Per-request timeout for Google API calls. Without it, a stalled connection
# blocks the fetch thread for minutes (observed ~30s+ per calendar).
GOOGLE_API_TIMEOUT_SECONDS = 15

from src.logger import logger
from src.models.internal import CalendarData
from src.models.external_apis import GoogleCalendarEventResponse
from src.models.enums import ApiParam, ApiValue, ApiResponseKey


class GoogleCalendarService:
    """Service to fetch Google Calendar events using Service Account authentication."""

    def __init__(self, service_account_file: Path, calendar_configs: Dict[str, str], calendar_colors: Dict[str, str] | None = None):
        """
        Initialize the Google Calendar service.

        Args:
            service_account_file: Path to the service account JSON key file
            calendar_configs: Dict mapping calendar IDs to friendly names
            calendar_colors: Dict mapping calendar IDs to hex color strings
        """
        self.service_account_file = service_account_file
        self.calendar_configs = calendar_configs
        self.service = None
        self._calendar_colors: Dict[str, str] = calendar_colors or {}
        self._initialize_service()

    def _initialize_service(self):
        """Initialize the Google Calendar API service with Service Account credentials."""
        try:
            if not self.service_account_file.exists():
                logger.error(f"❌ Service account file not found: {self.service_account_file}")
                return

            credentials = service_account.Credentials.from_service_account_file(
                str(self.service_account_file),
                scopes=['https://www.googleapis.com/auth/calendar.readonly']
            )

            authed_http = AuthorizedHttp(
                credentials,
                http=httplib2.Http(timeout=GOOGLE_API_TIMEOUT_SECONDS)
            )
            self.service = build('calendar', 'v3', http=authed_http, cache_discovery=False)
            logger.info(f"✅ Google Calendar service initialized for {len(self.calendar_configs)} calendars")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Calendar service: {e}")
            self.service = None

    def fetch_events(self, days_ahead: int = 7) -> CalendarData:
        """
        Fetch calendar events from all configured calendars for the current month view.

        Fetches events for the entire month grid visible in the calendar, including:
        - Trailing days from previous month
        - All days of current month
        - Leading days from next month

        Args:
            days_ahead: Ignored - fetches for current month view instead

        Returns:
            CalendarData containing merged events from all calendars
        """
        if not self.service:
            logger.warning("⚠️ Google Calendar service not initialized")
            return CalendarData(events=[], updated=datetime.now().strftime("%H:%M:%S"))

        all_events = []

        # Get current date
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # Calculate the visible date range for the calendar grid
        # Start: First day shown in calendar (may be from previous month)
        first_day_of_month = datetime(current_year, current_month, 1)
        first_weekday = first_day_of_month.weekday()  # 0=Monday, 6=Sunday

        # Calculate how many days back we need to go to get to Monday
        days_back = first_weekday
        time_min_date = first_day_of_month - timedelta(days=days_back)

        # End: Last day shown in calendar (may extend into next month)
        # A month grid is typically 5-6 weeks = 35-42 days
        time_max_date = time_min_date + timedelta(days=42)

        # Convert to UTC ISO format with 'Z' suffix for Google API
        time_min = time_min_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        time_max = time_max_date.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + 'Z'

        logger.debug(f"📅 Fetching events from {time_min_date.date()} to {time_max_date.date()}")

        for calendar_id, calendar_name in self.calendar_configs.items():
            try:
                events_result = self.service.events().list(
                    **{
                        ApiParam.CALENDAR_ID.value: calendar_id,
                        ApiParam.TIME_MIN.value: time_min,
                        ApiParam.TIME_MAX.value: time_max,
                        ApiParam.MAX_RESULTS.value: 50,
                        ApiParam.SINGLE_EVENTS.value: True,
                        ApiParam.ORDER_BY.value: ApiValue.ORDER_BY_START_TIME.value,
                        ApiParam.TIME_ZONE.value: ApiValue.TIMEZONE_PRAGUE.value
                    }
                ).execute()

                events = events_result.get(ApiResponseKey.ITEMS.value, [])

                for event_data in events:
                    # Parse using typed model
                    event_response = GoogleCalendarEventResponse.from_dict(event_data)
                    # Convert to internal model with calendar info and calendar-level color
                    cal_color = self._calendar_colors.get(calendar_id)
                    calendar_event = event_response.to_calendar_event(calendar_id, calendar_name, cal_color)
                    all_events.append(calendar_event)

                logger.debug(f"📅 Fetched {len(events)} events from calendar: {calendar_name}")

            except HttpError as error:
                logger.error(f"❌ HTTP error fetching events from {calendar_name}: {error}")
                # Check if it's an authentication/permission issue
                if error.resp.status in [401, 403]:
                    logger.error(f"⚠️ Calendar '{calendar_name}' may not be shared with service account")
            except socket.timeout:
                logger.error(f"❌ Timeout fetching events from {calendar_name}")
            except Exception as e:
                logger.error(f"❌ Unexpected error fetching calendar events from {calendar_name}: {e}", exc_info=True)

        all_events.sort(key=lambda e: e.start)

        updated_time = datetime.now().strftime("%H:%M:%S")
        logger.info(f"📅 Total events fetched: {len(all_events)} from {len(self.calendar_configs)} calendars")

        return CalendarData(events=all_events, updated=updated_time)

    async def fetch_events_async(self) -> CalendarData:
        """
        Async wrapper for fetch_events to avoid blocking the event loop.

        Fetches events for the entire current month view.

        Returns:
            CalendarData containing merged events from all calendars
        """
        return await asyncio.to_thread(self.fetch_events)
