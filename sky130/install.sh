# From https://github.com/sgherbst/sky130-hello-world

# install magic
git clone https://github.com/RTimothyEdwards/magic.git
cd magic
git checkout magic-8.3
./configure
make
sudo make install
cd ..

# install netgen
git clone https://github.com/RTimothyEdwards/netgen.git
cd netgen
git checkout netgen-1.5
./configure
make
sudo make install
cd ..

# install skywater-pdk
git clone https://github.com/google/skywater-pdk
cd skywater-pdk
git submodule init libraries/sky130_fd_pr/latest
git submodule update
cd ..

# install open_pdks
git clone https://github.com/RTimothyEdwards/open_pdks.git
cd open_pdks
./configure --enable-sky130-pdk=`realpath ../skywater-pdk` --with-sky130-local-path=`realpath ../PDKS`
make
make install
cd ..
