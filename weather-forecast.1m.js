#!/opt/homebrew/bin/node

const https = require('https');
const fs = require('fs');
const path = require('path');

let API_KEY, CITY_LAT, CITY_LON, CITY_NAME, CITY_LABEL;
try {
  const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'openweathermap.conf.json'), 'utf8'));
  API_KEY = config.API_KEY;
  CITY_LAT = config.LAT;
  CITY_LON = config.LON;
  CITY_NAME = config.CITY;
  CITY_LABEL = config.LABEL;
} catch (e) {
  console.log('🌤️ Weather Error | color=red');
  console.log('---');
  console.log('❌ Could not read openweathermap.conf.json');
  process.exit(0);
}

const CURRENT_WEATHER_URL = `https://api.openweathermap.org/data/2.5/weather?q=${CITY_NAME}&appid=${API_KEY}&units=metric`;
const FORECAST_URL = `https://api.openweathermap.org/data/2.5/forecast?q=${CITY_NAME}&appid=${API_KEY}&units=metric`;
const HOURLY_FORECAST_URL = `https://pro.openweathermap.org/data/2.5/forecast/hourly?q=${CITY_NAME}&appid=${API_KEY}&units=metric`;

// Weather icon mapping
const WEATHER_ICONS = {
  '01d': '☀️', '01n': '🌙',     // clear sky
  '02d': '⛅', '02n': '☁️',     // few clouds
  '03d': '☁️', '03n': '☁️',     // scattered clouds
  '04d': '☁️', '04n': '☁️',     // broken clouds
  '09d': '🌧️', '09n': '🌧️',     // shower rain
  '10d': '🌦️', '10n': '🌧️',     // rain
  '11d': '⛈️', '11n': '⛈️',     // thunderstorm
  '13d': '🌨️', '13n': '🌨️',     // snow
  '50d': '🌫️', '50n': '🌫️'      // mist
};

function getWeatherIcon(iconCode) {
  return WEATHER_ICONS[iconCode] || '🌤️';
}

function formatTemperature(temp) {
  return `${Math.round(temp)}°C`;
}

function capitalizeFirst(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatDay(timestamp) {
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-US', { weekday: 'short' });
}

function formatHour(timestamp) {
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function getTodayHourlyForecast(forecastData) {
  const today = new Date().toDateString();
  return forecastData.list.filter(item => {
    const itemDate = new Date(item.dt * 1000);
    return itemDate.toDateString() === today;
  });
}

async function makeAPIRequest(url) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, (response) => {
      let data = '';

      response.on('data', (chunk) => {
        data += chunk;
      });

      response.on('end', () => {
        try {
          const result = {
            statusCode: response.statusCode,
            data: response.statusCode === 200 ? JSON.parse(data) : null,
            error: response.statusCode !== 200 ? `HTTP ${response.statusCode}: ${response.statusMessage}` : null
          };
          resolve(result);
        } catch (error) {
          reject(`Error parsing JSON: ${error.message}`);
        }
      });
    });

    request.on('error', (error) => {
      reject(`Connection error: ${error.message}`);
    });

    request.setTimeout(10000, () => {
      request.destroy();
      reject('Timeout: Request took more than 10 seconds');
    });
  });
}

function processForecast(forecastData) {
  const dailyData = {};

  // Group forecasts by day (take midday forecast for each day)
  forecastData.list.forEach(item => {
    const date = new Date(item.dt * 1000);
    const dateKey = date.toDateString();
    const hour = date.getHours();

    // Take forecast around midday (12:00) for daily representation
    if (hour >= 11 && hour <= 14) {
      if (!dailyData[dateKey] || hour === 12) {
        dailyData[dateKey] = item;
      }
    }
  });

  return Object.values(dailyData).slice(0, 5); // Next 5 days
}

async function main() {
  try {

    const [currentResult, forecastResult, hourlyResult] = await Promise.all([
      makeAPIRequest(CURRENT_WEATHER_URL),
      makeAPIRequest(FORECAST_URL),
      makeAPIRequest(HOURLY_FORECAST_URL)
    ]);

    if (currentResult.statusCode !== 200 || forecastResult.statusCode !== 200) {
      throw new Error('Failed to fetch weather data from both APIs');
    }

    const currentWeather = currentResult.data;
    const forecast = forecastResult.data;
    const hourlyForecast = hourlyResult.statusCode === 200 ? hourlyResult.data : forecast;

    const currentTemp = formatTemperature(currentWeather.main.temp);
    const currentIcon = getWeatherIcon(currentWeather.weather[0].icon);
    const currentDesc = capitalizeFirst(currentWeather.weather[0].description);

    // Main line in menu bar
    console.log(`${currentIcon} ${currentTemp} | size=14`);
    console.log('---');

    // Current weather details
    console.log(`🌡️ ${currentTemp} - ${currentDesc}`);
    console.log(`🌡️ Feels like: ${formatTemperature(currentWeather.main.feels_like)}`);
    console.log(`🌬️ Wind: ${currentWeather.wind.speed} m/s`);
    console.log(`💧 Humidity: ${currentWeather.main.humidity}%`);
    console.log(`👁️ Visibility: ${(currentWeather.visibility / 1000).toFixed(1)} km`);
    console.log('---');

    // Today's hourly forecast
    const hourlyToday = getTodayHourlyForecast(hourlyForecast);
    if (hourlyToday.length > 0) {
      console.log('🕐 Today by hour:');
      hourlyToday.forEach(item => {
        const hour = formatHour(item.dt);
        const temp = formatTemperature(item.main.temp);
        const icon = getWeatherIcon(item.weather[0].icon);
        const desc = capitalizeFirst(item.weather[0].description);
        console.log(`${icon} ${hour}: ${temp} - ${desc} | size=12`);
      });
      console.log('---');
    }

    // 5-day forecast
    console.log('📅 5-Day Forecast:');
    const dailyForecasts = processForecast(forecast);

    dailyForecasts.forEach(day => {
      const dayName = formatDay(day.dt);
      const temp = formatTemperature(day.main.temp);
      const icon = getWeatherIcon(day.weather[0].icon);
      const desc = capitalizeFirst(day.weather[0].description);

      console.log(`${icon} ${dayName}: ${temp} - ${desc} | size=12`);
    });

    console.log('---');
    console.log('🔄 Refresh | refresh=true');
    console.log(`📍 ${CITY_LABEL}`);

  } catch (error) {
    console.log('🌤️ Weather Error | color=red');
    console.log('---');
    console.log(`❌ ${error}`);
    console.log('🔄 Retry | refresh=true');
    console.log('---');
    console.log('💡 Tips:');
    console.log('• Check internet connection');
    console.log('• Verify API key is valid');
  }
}

main();