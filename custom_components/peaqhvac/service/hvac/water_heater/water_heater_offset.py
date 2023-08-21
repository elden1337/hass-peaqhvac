prices = [0.34, 0.32, 0.32, 0.31, 0.32, 0.35, 0.37, 0.45, 0.51, 0.57, 0.56, 0.52, 0.5, 0.46, 0.45, 0.45, 0.45, 0.49,
          0.53, 0.54, 0.53, 0.46, 0.38, 0.36]
prices_tomorrow = [0.36, 0.35, 0.34, 0.34, 0.35, 0.35, 0.39, 0.45, 0.48, 0.48, 0.48, 0.47, 0.46, 0.44, 0.42, 0.43, 0.45,
                   0.48, 0.48, 0.51, 0.5, 0.48, 0.43, 0.42]

from datetime import datetime, timedelta


def get_hourly_price_category(current_hour, prices_today, prices_tomorrow):
    prices = prices_today + prices_tomorrow
    current_price = prices[current_hour]
    next_three_hours_prices = prices[current_hour + 1:current_hour + 4] + prices[:3]
    next_three_hours_avg_price = sum(next_three_hours_prices) / len(next_three_hours_prices)
    price_range = max(prices) - min(prices)
    category_size = price_range / 3
    if current_price < min(prices) + category_size:
        return 'low'
    elif current_price < min(prices) + 2 * category_size:
        return 'mid'
    else:
        if current_price > next_three_hours_avg_price:
            return 'high'
        else:
            return 'mid'


for i in range(0, 24):
    print(i, get_hourly_price_category(i, prices, prices_tomorrow))