/**
 * Weather module
 * Handles weather icon mapping and background updates
 */

/**
 * Get the Lucide icon name for a weather code
 * @param {number} code - Weather code from API
 * @returns {string} Lucide icon name
 */
function getWeatherIconName(code) {
    if (code === 0) return WeatherIcon.SUN;
    if (code >= 1 && code <= 3) return WeatherIcon.CLOUD_SUN;
    if (code >= 45 && code <= 48) return WeatherIcon.CLOUD;
    if (code >= 51 && code <= 67) return WeatherIcon.CLOUD_RAIN;
    if (code >= 71 && code <= 77) return WeatherIcon.CLOUD_SNOW;
    if (code >= 80 && code <= 82) return WeatherIcon.CLOUD_RAIN;
    if (code >= 85 && code <= 86) return WeatherIcon.CLOUD_SNOW;
    if (code >= 95 && code <= 99) return WeatherIcon.CLOUD_LIGHTNING;
    return WeatherIcon.CLOUD;
}

/**
 * Update weather panel background based on weather conditions
 * @param {number} code - Weather code
 * @param {boolean} isDay - Whether it's daytime
 */
function updateWeatherBackground(code, isDay) {
    const panel = document.getElementById(ElementId.WEATHER_RECT);
    if (!panel) return;
    panel.className = CssClass.RECT; // reset classes

    let mood = '';
    if (code === 0 || code === 1) {
        mood = isDay ? CssClass.BG_CLEAR_DAY : CssClass.BG_CLEAR_NIGHT;
    } else if (code >= 2 && code <= 48) {
        mood = CssClass.BG_CLOUDY;
    } else if (code >= 51 && code <= 67 || code >= 80 && code <= 82) {
        mood = CssClass.BG_RAINY;
    } else if (code >= 71 && code <= 77 || code >= 85 && code <= 86) {
        mood = CssClass.BG_SNOWY;
    } else if (code >= 95) {
        mood = CssClass.BG_STORM;
    }
    if (mood) panel.classList.add(mood);
}

// Export for use in other modules
window.getWeatherIconName = getWeatherIconName;
window.updateWeatherBackground = updateWeatherBackground;
