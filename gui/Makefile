# Bump this and package.json version at the same time.
ELECTRON_VERSION=0.34.3
OSX_ARCH=x64
BUILD_DIR=build
OSX_BUNDLE_BASE=$(BUILD_DIR)/Lektor-darwin-$(OSX_ARCH)
OSX_BUNDLE=$(OSX_BUNDLE_BASE)/Lektor.app
OSX_BUNDLE_RES=$(OSX_BUNDLE)/Contents/Resources

REBUILD_CMD=./node_modules/.bin/electron-rebuild -w runas

npm-install:
	npm install
	$(REBUILD_CMD)

run-only:
	./bin/run

run: npm-install run-only

$(BUILD_DIR)/Python.framework:
	./bin/compile-python-framework

build-wheels: $(BUILD_DIR)/Python.framework
	./bin/build-wheels

vendor/ImageMagick-x86_64-apple-darwin15.0.0.tar.gz:
	cd vendor; wget http://www.imagemagick.org/download/binaries/ImageMagick-x86_64-apple-darwin15.0.0.tar.gz
	cd vendor; tar xzf ImageMagick-x86_64-apple-darwin15.0.0.tar.gz

osx-bundle: vendor/ImageMagick-x86_64-apple-darwin15.0.0.tar.gz build-wheels
	npm install --production
	$(REBUILD_CMD)
	cd static; ../node_modules/.bin/webpack
	./node_modules/.bin/electron-packager . Lektor --platform=darwin \
		--ignore='(node_modules|vendor|resources|bin|build)' \
		--arch=$(OSX_ARCH) --version=$(ELECTRON_VERSION) \
		--overwrite --out=$(BUILD_DIR)
	cp resources/Lektor-Info.plist $(OSX_BUNDLE)/Contents/Info.plist
	cp resources/Icon.icns $(OSX_BUNDLE_RES)
	mkdir $(OSX_BUNDLE_RES)/local
	cp -R vendor/ImageMagick-6.9.2/* $(OSX_BUNDLE_RES)/local
	cp resources/lektor-mac-proxy $(OSX_BUNDLE)/Contents/MacOS/lektor-proxy
	cp resources/lektor $(OSX_BUNDLE_RES)/lektor
	rm -rf $(OSX_BUNDLE_RES)/local/share/man
	rm -rf $(OSX_BUNDLE_RES)/local/share/doc
	rm -rf $(OSX_BUNDLE_RES)/local/include
	rm $(OSX_BUNDLE_RES)/atom.icns
	rm -rf $(OSX_BUNDLE_RES)/default_app
	# Manually copy over native modules we depend on
	mkdir -p $(OSX_BUNDLE_RES)/app/node_modules
	cp -R node_modules/runas $(OSX_BUNDLE_RES)/app/node_modules/runas
	cp -R $(BUILD_DIR)/Python.framework $(OSX_BUNDLE)/Contents/Frameworks/Python.framework
	./bin/make-python-framework-relocatable $(OSX_BUNDLE)/Contents/Frameworks/Python.framework
	./bin/install-wheels $(OSX_BUNDLE)/Contents/Frameworks/Python.framework/Versions/Current/lib/python2.7/site-packages
	mkdir $(OSX_BUNDLE_RES)/lektor-dist

node_modules/.bin/appdmg:
	npm install appdmg

osx-dmg: node_modules/.bin/appdmg osx-bundle
	rm -rf $(OSX_BUNDLE_BASE)/Lektor.dmg
	./node_modules/.bin/appdmg dmg-config.json $(OSX_BUNDLE_BASE)/Lektor.dmg
