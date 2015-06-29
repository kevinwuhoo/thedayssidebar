$(document).ready(function() {

  $.getJSON('http://thedayssidebar.herokuapp.com', null, function(data) {

    var palette = data.palette;
    var sidebar = data.sidebar;

    // setting of background colors
    $('.bg-left').css('background-color', palette.bg_left);
    $('.bg-right').css('background-color', palette.bg_right);

    // setting of palette colors and sidebar titles/links, activate tooltips
    for(var i = 0; i < 5; i++) {
      $('.color').eq(i).css('background-color', palette['colors'][i]);
      $('.preview').eq(i).find('.bg-text').text(sidebar[i]['title']);
      $('.palette a').eq(i).attr('href', sidebar[i]['url']);
      $('.preview').eq(i).find('.bg-img').attr('src', sidebar[i]['image_url']);
    }

    // determine if text color should be dark or light depending on background
    $('.info-left').css('color', determineTextColor(palette.bg_left));
    $('.info-right').css('color', determineTextColor(palette.bg_right));

    // add current to the left panel
    date = new Date();
    $('.the-date').text(
      [padNumber(date.getDate()), padNumber(date.getMonth() + 1),
       date.getFullYear()].join(' / ')
    );
    window.setInterval(function updateTime() {
      date = new Date();
      $('.the-time').text(
        [padNumber(date.getHours()), padNumber(date.getMinutes()),
         padNumber(date.getSeconds())].join(' : ')
      );
      return updateTime;
    }(), 1000);

    // add source of inspiration to the right panel
    $('.inspiration').text(palette.inspiration);

    // fadein of background, followed by palette and then info text
    $('.bg-left').fadeIn('fast').css('display', 'inline-block');
    $('.bg-right').fadeIn('fast').css('display', 'inline-block');

    window.setTimeout(function() {
      $('.palette').fadeIn('fast');
    }, 250);

    window.setTimeout(function() {
      $('.info').fadeIn('fast');
    }, 750);

    $('.color').hover(
      function() {
        var colorIndex = $(this).attr('data-color-index');
        $('.preview[data-color-index=' + colorIndex + ']').fadeIn('fast');
      }, function() {
        $('.preview').fadeOut('fast');
      }
    );
  });
});

// http://stackoverflow.com/a/3943023
function determineTextColor(hex) {
  rgb = hexToRgb(hex);
  var c = {};
  for(color in rgb) {
      var value = rgb[color];
      value = value / 255.0;
      if(value <= 0.03928)
        c[color] = value / 12.92;
      else
        c[color] = Math.pow((value + 0.055) / 1.055, 2.4);
  }

  L = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;
  if(L > 0.179)
    return '#000000';
  else
    return '#FFFFFF';
}

// http://stackoverflow.com/a/5624139
function hexToRgb(hex) {
    var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
    hex = hex.replace(shorthandRegex, function(m, r, g, b) {
        return r + r + g + g + b + b;
    });

    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

// pads numbers/strings to 2 digits
function padNumber(n) {
  var str = '' + n;
  var pad = '00';
  return pad.substring(0, pad.length - str.length) + str;
}
