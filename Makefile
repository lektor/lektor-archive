all: test

pex:
	virtualenv pex-build-cache
	pex-build-cache/bin/pip install --upgrade pip
	pex-build-cache/bin/pip install pex requests wheel
	pex-build-cache/bin/pip wheel -w pex-build-cache/wheelhouse .
	pex-build-cache/bin/pex \
		-v -o lektor.pex -e lektor.cli:cli \
		-f pex-build-cache/wheelhouse \
		--disable-cache \
		--not-zip-safe Lektor
	rm -rf pex-build-cache

test:
	@cd tests; py.test . --tb=short

osx-dmg:
	$(MAKE) -C gui osx-dmg
