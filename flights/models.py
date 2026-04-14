from dataclasses import dataclass


@dataclass
class Deal:
    origin_iata: str
    origin_name: str
    country: str
    outbound_date: str     # "2024-05-01"
    outbound_day: str      # "Wednesday"
    outbound_dep: str      # "07:15"
    outbound_arr: str      # "11:30"
    outbound_airline: str  # "Transavia"
    outbound_stops: int
    outbound_price_eur: float
    return_date: str
    return_iata: str         # airport the return lands at (may differ from origin_iata)
    return_name: str
    return_dep: str
    return_arr: str
    return_airline: str
    return_stops: int
    return_price_eur: float
    price_eur: float

    def to_dict(self) -> dict:
        return {
            "origin_iata": self.origin_iata,
            "origin_name": self.origin_name,
            "country": self.country,
            "outbound_date": self.outbound_date,
            "outbound_day": self.outbound_day,
            "outbound_dep": self.outbound_dep,
            "outbound_arr": self.outbound_arr,
            "outbound_airline": self.outbound_airline,
            "outbound_stops": self.outbound_stops,
            "outbound_price_eur": self.outbound_price_eur,
            "return_date": self.return_date,
            "return_iata": self.return_iata,
            "return_name": self.return_name,
            "return_dep": self.return_dep,
            "return_arr": self.return_arr,
            "return_airline": self.return_airline,
            "return_stops": self.return_stops,
            "return_price_eur": self.return_price_eur,
            "price_eur": self.price_eur,
        }
