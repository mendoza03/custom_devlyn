/** @odoo-module **/
// import MapWidget from "@real_estate_bits/js/map_widget.js" 

import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { Component, onWillStart, onMounted, useState, useRef, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class place_autocomplete extends CharField {
    static template = "AutoComplete";
    setup() {
        super.setup();
        this.lat = 50.862117;
        this.lng = 4.416593;

        this.hasGoogle = useState({val: false});
        this.orm = useService("orm");
        this.gmapContainer = useRef("gmapContainer");

        // onWillStart(async() => {
        //     if (typeof google == "undefined") {
        //         let key = await this.orm.call("gmap.config", "get_key_api", [], {});
        //         $.getScript("https://maps.googleapis.com/maps/api/js?key=" + key + "&libraries=places&callback=Function.prototype");
        //     }
        // });

        // onMounted(() => {
        //     const self = this;
        //     if(this?.input?.el) {
        //         $(this?.input?.el).parent().removeClass("oe_inline");
        //     }
        //     this.t = setInterval(function () {
        //         if (typeof google !== "undefined") {
        //             self.hasGoogle.val = true;
        //             self.on_ready();
        //         }
        //     }, 1000);
        // })

        // useEffect(() => {
        //     if (this?.input?.el?.value && typeof google !== "undefined") {
        //         this.on_ready();
        //     }
        // }, () => [this?.input?.el?.value])
    }

    on_ready() {
        var self = this;
        if (self.t) {
            clearInterval(self.t);
        }

        var geocoder = new google.maps.Geocoder();
            geocoder.geocode({ address: this.input.el.value }, function (
            results,
            status
        ) {
            if (status === "OK") {
                self.lat = results[0].geometry.location.lat();
                self.lng = results[0].geometry.location.lng();
            }
        });

        var autocomplete = new google.maps.places.Autocomplete(this.input.el, {
            types: ["geocode"],
        });

        autocomplete.addListener("place_changed", function () {
            var place = autocomplete.getPlace();

            if (!place.geometry || !place.geometry.location) {
                return;
            }

            var location = place.geometry.location;
            self.lat = location.lat();
            self.lng = location.lng();
        });

        var latLng = new google.maps.LatLng(self.lat, self.lng);

        var mapOptions = {
            zoom: 12,
            center: latLng,
        };
        this.map = new google.maps.Map(
            self.gmapContainer.el,
            mapOptions
        );

        this.marker = new google.maps.Marker({
            position: latLng,
            map: self.map,
            draggable: true,
        });

        // Click event
        this.map.addListener("click", function (event) {
            var lat = event.latLng.lat();
            var lng = event.latLng.lng();
            // Update marker
            var latLng = new google.maps.LatLng(lat, lng);
            self.marker.setPosition(latLng);
            google.maps.event.trigger(self.map, "resize");
            // Update place
            self.update_place(lat, lng);
        });

        this.map.addListener("rightclick", function (event) {
            alert("Lat: " + event.latLng.lat() + " , Lng: " + event.latLng.lng());
        });

        // Marker drag event
        this.marker.addListener("dragend", function (event) {
            var lat = event.latLng.lat();
            var lng = event.latLng.lng();
            self.update_place(lat, lng);
        });

        this.gmapContainer.el.addEventListener('click', () => {
            // $(self.gmapContainer.el).toggle();
            self.update_marker(self.lat, self.lng);
        })
    }

    update_place(lat, lng) {
        var self = this;

        if (lat === this.lat && lng === this.lng) {
            return;
        }

        this.lat = lat;
        this.lng = lng;

        var geocoder = new google.maps.Geocoder();
        var latLng = new google.maps.LatLng(lat, lng);
        geocoder.geocode({ location: latLng }, function (results, status) {
            if (status === "OK") {
                if (self.input.el) {
                    $(self.input.el).val(results[0].formatted_address);
                }
            }
        });
    }

    update_marker(lat, lng) {
        this.lat = lat;
        this.lng = lng;
        var latLng = new google.maps.LatLng(lat, lng);
        this.map.setCenter(latLng);
        this.marker.setPosition(latLng);
        google.maps.event.trigger(this.map, "resize");
    }

    toggleMap(ev) {
        $(this.gmapContainer.el).toggle();
        this.update_marker(this.lat, this.lng);
    }
}

const autocompleteField = {
    ...charField,
    component: place_autocomplete
}

registry.category("fields").add("place_autocomplete", autocompleteField);