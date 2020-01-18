// Draggable right border for the second column
(function () {
  let div = document.getElementById('resize-drag');
  let grid = document.getElementById('grid-container');
  let columns = Array.from(grid.children);
  let explorerIdx = 1;
  let colWidths;
  let isPressed = false;
  div.addEventListener('mousedown', function (e) {
    isPressed = true;
    colWidths = columns.map(elem => elem.offsetWidth);
    curX = e.pageX;
  });
  document.addEventListener('mousemove', function (e) {
    if (isPressed) {
      let diff = e.pageX - curX;
      curX = e.pageX;
      colWidths[explorerIdx] += diff;
      grid.style.gridTemplateColumns = colWidths.map(
        (n, i) => i === explorerIdx + 1 ? 'auto' : n + 'px'
      ).join(' ');
    }
  });
  document.addEventListener('mouseup', function () {
    isPressed = false;
  });
})();

// change menus
(function () {
  let menuEntries = document.getElementsByClassName('menu-entry');
  for (let elem of document.querySelectorAll("#panel-menu ul > li > div")) {
    let target = document.getElementById(elem.getAttribute('data-menu-id'));
    elem.addEventListener("click", function () {
      for (let menuEntry of menuEntries) menuEntry.style.display = 'none';
      target.style.display = 'block';
    });
  }
})();

// some global variables to keep track of state
const ImageProperties = {
  // variable for the picture currently displayed
  // must be a <li> element
  currentImage: null,
  // variable for the zoom level
  zoomLevel: 1.0
};

// get files in directory
// fileTree is a <ul> element
// path must already be URL encoded
function fetchDirectory(fileTree, path) {
  const TRIANGLE_RIGHT = '\u25B6';
  const TRIANGLE_DOWN = '\u25BC';
  const root = document.getElementById('file-tree');
  let url = '/fs?path=' + path;
  if (fileTree === root) url += '&linkprev=true';
  fetch(
    url
  ).then(resp =>
    resp.text()
  ).then(html => {
    fileTree.innerHTML = html;
    for (let spanContainer of fileTree.querySelectorAll(
      'li[class^=folder-] > .fs-item-container')) {
      const li = spanContainer.parentElement;
      const spanCaret = spanContainer.querySelector('.caret');
      const folderName = spanContainer.querySelector('.fs-item-text').textContent.trim();
      spanContainer.addEventListener('click', function () {
        li.classList.toggle('folder-active');
        li.classList.toggle('folder-inactive');
        if (li.classList.contains('folder-active')) {
          spanCaret.textContent = TRIANGLE_DOWN;
          if (li.querySelector('ul') === null) {
            let ul;
            if (folderName === '..') {
              while (root.firstChild) root.removeChild(root.firstChild);
              ul = root;
            } else {
              ul = document.createElement('ul');
              li.appendChild(ul);
            }
            fetchDirectory(ul, path + '/' + encodeURIComponent(folderName));
          }
        } else {
          spanCaret.textContent = TRIANGLE_RIGHT;
        }
      });
    }
    for (let spanContainer of document.querySelectorAll(
      'li.fs-image > .fs-item-container')) {
      const li = spanContainer.parentElement;
      const fileName = spanContainer.querySelector('.fs-item-text').textContent.trim();
      addOCREvent(li, path + '/' + encodeURIComponent(fileName));
    }
  }).catch(err => {
    console.error(err);
  });
}

// initially, the current directory should be displayed
fetchDirectory(document.getElementById('file-tree'), '.');

// dictionary lookup callback
function dictLookup() {
  const ocrTextBox = document.querySelector('#ocr-explorer-text input');
  const wordList = document.getElementById('word-list');
  fetch(
    '/dict?text=' + encodeURIComponent(ocrTextBox.value)
  ).then(resp =>
    resp.text()
  ).then(html => {
    wordList.innerHTML = html;
  }).catch(err => {
    console.error(err);
  });
}

// add event listener for input change
(function () {
  const ocrTextBox = document.querySelector('#ocr-explorer-text input');
  ocrTextBox.addEventListener('input', dictLookup);
})();

// request OCR information for a specific image
function addOCREvent(li, path) {
  // utility function for extracting basename of a file path
  function basename(path) {
    let i = path.lastIndexOf('/');
    return i === -1 ? path : path.substring(i + 1);
  }
  const imageContainer = document.getElementById('image-container');
  const ocrTextBox = document.querySelector('#ocr-explorer-text input');
  const imageFilenameElt = document.getElementById('image-filename');
  const loadingElt = document.getElementById('loading-text');
  li.addEventListener('click', function () {
    loadingElt.style.display = 'block';
    imageFilenameElt.textContent = '';
    imageContainer.style.width = '';
    imageContainer.style.height = '';
    // remove boxes for the previous image
    while (imageContainer.firstChild)
      imageContainer.removeChild(imageContainer.firstChild);
    imageContainer.style.backgroundImage = 'none';
    fetch(
      '/ocr?path=' + path
    ).then(resp =>
      resp.json()
    ).then(data => {
      loadingElt.style.display = 'none';
      imageContainer.style.backgroundImage = `url('/fs/images?path=${path}')`;
      imageContainer.setAttribute('data-orig-width', data.imageWidth);
      imageContainer.setAttribute('data-orig-height', data.imageHeight);
      imageFilenameElt.textContent = decodeURIComponent(basename(path));
      for (let box of data.boxes) {
        let div = document.createElement('div');
        div.className = 'ocr-box';
        div.title = box.text;
        div.setAttribute('data-orig-top', box.top);
        div.setAttribute('data-orig-left', box.left);
        div.setAttribute('data-orig-width', box.width);
        div.setAttribute('data-orig-height', box.height);
        // Make text appear in the input box when it is clicked
        div.addEventListener("click", function (e) {
          if (e.ctrlKey)
            ocrTextBox.value += box.text;
          else
            ocrTextBox.value = box.text;
          // apparently the event isn't triggered if we change the value
          // through javascript, so we have to manually call it
          dictLookup();
        });
        imageContainer.appendChild(div);
      }
      // update the current picture
      ImageProperties.currentImage = li;
      // reset zoom level
      ImageProperties.zoomLevel = 1.0;
      // actually set the style width/height of the image and boxes
      setZoom(ImageProperties.zoomLevel);
    }).catch(err => {
      console.error(err);
    });
  });
}

// set zoom levels of image and text boxes
function setZoom(factor) {
  function scaleAttr(attr, factor) {
    return Math.floor(parseInt(attr) * factor) + 'px';
  }
  const imageContainer = document.getElementById('image-container');
  if (imageContainer.style.backgroundImage) {
    imageContainer.style.width = scaleAttr(
      imageContainer.getAttribute('data-orig-width'), factor);
    imageContainer.style.height = scaleAttr(
      imageContainer.getAttribute('data-orig-height'), factor);
    for (let box of document.getElementsByClassName('ocr-box')) {
      box.style.top = scaleAttr(box.getAttribute('data-orig-top'), factor);
      box.style.left = scaleAttr(box.getAttribute('data-orig-left'), factor);
      box.style.width = scaleAttr(box.getAttribute('data-orig-width'), factor);
      box.style.height = scaleAttr(box.getAttribute('data-orig-height'), factor);
    }
  }
}

// go to the previous/next picture
(function () {
  document.getElementById('image-controls-left').addEventListener(
    'click', function () {
      if (ImageProperties.currentImage &&
        ImageProperties.currentImage.previousElementSibling) {
        ImageProperties.currentImage.previousElementSibling.click();
      }
    }
  );
  document.getElementById('image-controls-right').addEventListener(
    'click', function () {
      if (ImageProperties.currentImage &&
        ImageProperties.currentImage.nextElementSibling) {
        ImageProperties.currentImage.nextElementSibling.click();
      }
    }
  );
})();

// zoom in/out controls
(function () {
  const ZOOM_MIN = 0.1;
  const ZOOM_MAX = 3.0;
  const ZOOM_INCREMENT = 0.1;
  document.getElementById('zoom-out').addEventListener(
    'click', function () {
      if (ImageProperties.currentImage && ImageProperties.zoomLevel > ZOOM_MIN)
        setZoom((ImageProperties.zoomLevel -= ZOOM_INCREMENT));
    }
  );
  document.getElementById('zoom-in').addEventListener(
    'click', function () {
      if (ImageProperties.currentImage && ImageProperties.zoomLevel < ZOOM_MAX)
        setZoom((ImageProperties.zoomLevel += ZOOM_INCREMENT));
    }
  );
})();
