from bs4 import BeautifulSoup
import requests
import logging


def fetch_rate(url: str) -> list[str]:
    """
    Fetch rates from a specific URL.

    Args:
        url (str): The URL to fetch rates from.

    Returns:
        list[str]: A list of extracted rate values.
    """
    try:
        # Replace HTTPS with HTTP if required
        url = url.replace("https://", "http://")
        response = requests.get(url)
        response.raise_for_status()

        # Parse HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the table with border="1"
        table = soup.find("table", {"border": "1"})
        if not table:
            raise ValueError("Table with border='1' not found.")

        # Extract rates from rows
        rates = []
        rows = table.find_all("tr")
        for row in rows:
            cell = row.find("td")  # Get the first <td> in the row
            if cell:
                rates.append(cell.get_text(strip=True))

        logging.info(f"Fetched {len(rates)} rates from {url}.")
        return rates

    except requests.RequestException as e:
        logging.error(f"Error fetching data from the URL {url}: {e}")
    except ValueError as e:
        logging.error(f"Data extraction error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    return []  # Return an empty list on failure


if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/fetch_rate.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )
    test_url = "https://newdoc.nccu.edu.tw/teaschm/1011/statisticText.jsp-y=1002&tnum=101476&snum=000346021.htm"
    rates = fetch_rate(test_url)
    print("Extracted Rates:", rates)
