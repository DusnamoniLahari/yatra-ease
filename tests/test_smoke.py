def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Test Hotel" in response.data


def test_services_search_finds_one_hotel(client):
    response = client.get("/services?q=hotel")
    assert response.status_code == 200
    assert b"1 services found" in response.data


def test_unknown_page_shows_friendly_404(client):
    response = client.get("/nothing-here")
    assert response.status_code == 404
    assert b"Page not found" in response.data