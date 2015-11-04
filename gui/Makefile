ELECTRON_VERSION=0.34.2
OSX_ARCH=x64
BUILD_DIR=build
OSX_BUNDLE_BASE=$(BUILD_DIR)/Lektor-darwin-$(OSX_ARCH)
OSX_BUNDLE=$(OSX_BUNDLE_BASE)/Lektor.app
OSX_BUNDLE_RES=$(OSX_BUNDLE)/Contents/Resources

run:
	@npm install && ./bin/run

download-im:
	mkdir vendor
	cd vendor; wget http://www.imagemagick.org/download/binaries/ImageMagick-x86_64-apple-darwin15.0.0.tar.gz
	cd vendor; tar xzf ImageMagick-x86_64-apple-darwin15.0.0.tar.gz

osx-bundle:
	npm install --production
	cd static; ../node_modules/.bin/webpack
	./node_modules/.bin/electron-packager . Lektor --platform=darwin \
		--ignore='(node_modules|vendor|resources|bin|build)' \
		--arch=$(OSX_ARCH) --version=$(ELECTRON_VERSION) \
		--overwrite --out=$(BUILD_DIR)
	cp resources/Lektor-Info.plist $(OSX_BUNDLE)/Contents/Info.plist
	cp resources/Icon.icns $(OSX_BUNDLE_RES)
	mkdir $(OSX_BUNDLE_RES)/local
	cp -R vendor/ImageMagick-6.9.2/* $(OSX_BUNDLE_RES)/local
	rm -rf $(OSX_BUNDLE_RES)/local/share/man
	rm -rf $(OSX_BUNDLE_RES)/local/share/doc
	rm -rf $(OSX_BUNDLE_RES)/local/include
	rm $(OSX_BUNDLE_RES)/atom.icns
	rm -rf $(OSX_BUNDLE_RES)/default_app
	rmdir $(OSX_BUNDLE_RES)/*.lproj
	mkdir $(OSX_BUNDLE_RES)/lektor-dist
	cp ../lektor.pex $(OSX_BUNDLE_RES)/lektor-dist/lektor

node_modules/.bin/appdmg:
	npm install appdmg

osx-dmg: node_modules/.bin/appdmg
	rm -rf $(OSX_BUNDLE_BASE)/Lektor.dmg
	./node_modules/.bin/appdmg dmg-config.json $(OSX_BUNDLE_BASE)/Lektor.dmg
