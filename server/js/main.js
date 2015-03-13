/*
 * Copyright (C) 2014 Red Hat, Inc.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the licence, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program; if not, see <http://www.gnu.org/licenses/>.
 *
 * Author: Alberto Ruiz <aruiz@redhat.com>
 */

function populate_profile_list() {
  $.ajaxSetup({cache: false});
  $.getJSON ("/profiles/", function (data) {
    $("#profile-list").html ("");
    $.each (data, function (i, val) {
      console.log(val.url);
      var li = $('<li></li>', { text: val.displayName });
      $('<input>', {
        value: 'Remove',
        type:  'button',
        on: {
          click: function() {
            remove_profile(val);
          }
        }
      }).appendTo(li);
      li.appendTo($("#profile-list"));
    });
  });
}


function remove_profile(profile) {
  if (confirm('Are you sure you want to delete ' + profile.displayName)) {
    $.getJSON ("/profile/delete/" + profile.url, function (data) {
      populate_profile_list();
    });
  }
}

$(document).ready (populate_profile_list);
