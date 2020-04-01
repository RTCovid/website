from django.urls import reverse

import pytest


class TestUrls:
    @pytest.mark.urls("apps.dashboard.urls")
    def test_index(self, client):
        url = reverse("index")
        response = client.get(url)
        assert response.status_code == 200
