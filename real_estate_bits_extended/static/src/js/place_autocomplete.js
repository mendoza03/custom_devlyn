/** @odoo-module **/

import { place_autocomplete } from "@real_estate_bits/js/place_autocomplete";
import { patch } from "@web/core/utils/patch";

patch(place_autocomplete.prototype, {
    on_ready() {
        const self = this;
        if (self.t) {
            clearInterval(self.t);
        }
        const coords = this.input.el.value.split(";");
        self.lat = parseFloat(coords[0]);
        self.lng = parseFloat(coords[1]);

        var autocomplete = new google.maps.places.Autocomplete(this.input.el, {
            types: ["geocode"],
        });

        autocomplete.addListener("place_changed", function () {
            const place = autocomplete.getPlace();
    
            if (!place.geometry || !place.geometry.location) {
                return;
            }

            const location = place.geometry.location;
            self.lat = location.lat();
            self.lng = location.lng();
            self.update_marker(self.lat, self.lng);
        });

        const latLng = new google.maps.LatLng(self.lat, self.lng);
        const mapOptions = {
            zoom: 12,
            center: latLng,
        };
        this.map = new google.maps.Map(self.gmapContainer.el, mapOptions);

        this.marker = new google.maps.Marker({
            position: latLng,
            map: self.map,
            draggable: true,
        });

        this.map.addListener("click", function (event) {
            const lat = event.latLng.lat();
            const lng = event.latLng.lng();
            const latLng = new google.maps.LatLng(lat, lng);
            self.marker.setPosition(latLng);
            google.maps.event.trigger(self.map, "resize");
            self.update_place(lat, lng);
        });

        this.map.addListener("rightclick", function (event) {
            alert("Lat: " + event.latLng.lat() + " , Lng: " + event.latLng.lng());
        });

        this.marker.addListener("dragend", function (event) {
            const lat = event.latLng.lat();
            const lng = event.latLng.lng();
            self.update_place(lat, lng);
        });

        this.gmapContainer.el.addEventListener('click', () => {
            self.update_marker(self.lat, self.lng);
        });
    },
    update_place(lat, lng) {
        const self = this;
        if (lat === this.lat && lng === this.lng) {
            return;
        }
        this.lat = lat;
        this.lng = lng;
        const geocoder = new google.maps.Geocoder();
        const latLng = new google.maps.LatLng(lat, lng);
        geocoder.geocode({ location: latLng }, function (results, status) {
            if (status === "OK") {
                if (self.input.el) {
                    $(self.input.el).val(`${lat};${lng}`);
                }
            }
        });
    }
})