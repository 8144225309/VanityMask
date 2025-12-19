#---------------------------------------------------------------------
# Makefile for VanitySearch with Steganography Mode
#
# Original Author: Jean-Luc PONS
# Stego Mode: 2024
#
# Usage:
#   make gpu=1 CCAP=89 -j$(nproc)     # RTX 4090 (Ada)
#   make gpu=1 CCAP=86 -j$(nproc)     # RTX 3080 (Ampere)
#   make gpu=1 CCAP=75 -j$(nproc)     # RTX 2070 (Turing)
#   make gpu=1 -j$(nproc)             # Auto-detect (builds multiple archs)
#   make -j$(nproc)                   # CPU only
#
# Environment variables:
#   CUDA      - CUDA toolkit path (default: /usr/local/cuda)
#   CXXCUDA   - C++ compiler for CUDA (default: system g++)
#   CCAP      - Compute capability (e.g., 75, 86, 89)
#---------------------------------------------------------------------

SRC = Base58.cpp IntGroup.cpp main.cpp Random.cpp \
      Timer.cpp Int.cpp IntMod.cpp Point.cpp SECP256K1.cpp \
      Vanity.cpp GPU/GPUGenerate.cpp hash/ripemd160.cpp \
      hash/sha256.cpp hash/sha512.cpp hash/ripemd160_sse.cpp \
      hash/sha256_sse.cpp Bech32.cpp Wildcard.cpp

OBJDIR = obj

ifdef gpu

OBJET = $(addprefix $(OBJDIR)/, \
        Base58.o IntGroup.o main.o Random.o Timer.o Int.o \
        IntMod.o Point.o SECP256K1.o Vanity.o GPU/GPUGenerate.o \
        hash/ripemd160.o hash/sha256.o hash/sha512.o \
        hash/ripemd160_sse.o hash/sha256_sse.o \
        GPU/GPUEngine.o Bech32.o Wildcard.o)

else

OBJET = $(addprefix $(OBJDIR)/, \
        Base58.o IntGroup.o main.o Random.o Timer.o Int.o \
        IntMod.o Point.o SECP256K1.o Vanity.o GPU/GPUGenerate.o \
        hash/ripemd160.o hash/sha256.o hash/sha512.o \
        hash/ripemd160_sse.o hash/sha256_sse.o Bech32.o Wildcard.o)

endif

# Compiler settings
CXX = g++

# CUDA settings - auto-detect or use environment
CUDA ?= /usr/local/cuda
CXXCUDA ?= $(CXX)
NVCC = $(CUDA)/bin/nvcc

# Compute capability handling
ifdef CCAP
# User specified single architecture (e.g., CCAP=89)
ccap = $(CCAP)
GENCODE = -gencode=arch=compute_$(ccap),code=sm_$(ccap)
else
# Build for multiple architectures (Turing, Ampere, Ada)
GENCODE = -gencode=arch=compute_75,code=sm_75 \
          -gencode=arch=compute_80,code=sm_80 \
          -gencode=arch=compute_86,code=sm_86 \
          -gencode=arch=compute_89,code=sm_89
endif

# Compiler flags
ifdef gpu
ifdef debug
CXXFLAGS = -DWITHGPU -m64 -mssse3 -Wno-write-strings -g -I. -I$(CUDA)/include
NVCCFLAGS = -G -maxrregcount=0 --ptxas-options=-v --compile --compiler-options -fPIC -ccbin $(CXXCUDA) -m64 -g -I$(CUDA)/include $(GENCODE)
else
CXXFLAGS = -DWITHGPU -m64 -mssse3 -Wno-write-strings -O3 -I. -I$(CUDA)/include
NVCCFLAGS = -maxrregcount=0 --ptxas-options=-v --compile --compiler-options -fPIC -ccbin $(CXXCUDA) -m64 -O3 -I$(CUDA)/include $(GENCODE)
endif
LFLAGS = -lpthread -L$(CUDA)/lib64 -lcudart
else
ifdef debug
CXXFLAGS = -m64 -mssse3 -Wno-write-strings -g -I.
else
CXXFLAGS = -m64 -mssse3 -Wno-write-strings -O3 -I.
endif
LFLAGS = -lpthread
endif

#--------------------------------------------------------------------

ifdef gpu
$(OBJDIR)/GPU/GPUEngine.o: GPU/GPUEngine.cu GPU/GPUCompute.h GPU/GPUMath.h GPU/GPUHash.h GPU/GPUEngine.h StegoTarget.h
	$(NVCC) $(NVCCFLAGS) -o $(OBJDIR)/GPU/GPUEngine.o -c GPU/GPUEngine.cu
endif

$(OBJDIR)/%.o : %.cpp
	$(CXX) $(CXXFLAGS) -o $@ -c $<

# Header dependencies for stego mode
$(OBJDIR)/main.o: main.cpp StegoTarget.h Vanity.h
$(OBJDIR)/Vanity.o: Vanity.cpp Vanity.h StegoTarget.h

all: VanitySearch

VanitySearch: $(OBJET)
	@echo Making VanitySearch...
	$(CXX) $(OBJET) $(LFLAGS) -o VanitySearch

$(OBJET): | $(OBJDIR) $(OBJDIR)/GPU $(OBJDIR)/hash

$(OBJDIR):
	mkdir -p $(OBJDIR)

$(OBJDIR)/GPU: $(OBJDIR)
	cd $(OBJDIR) && mkdir -p GPU

$(OBJDIR)/hash: $(OBJDIR)
	cd $(OBJDIR) && mkdir -p hash

clean:
	@echo Cleaning...
	@rm -f obj/*.o
	@rm -f obj/GPU/*.o
	@rm -f obj/hash/*.o
	@rm -f VanitySearch

# Show configuration
info:
	@echo "CUDA Path: $(CUDA)"
	@echo "NVCC: $(NVCC)"
	@echo "C++ Compiler: $(CXX)"
	@echo "CUDA C++ Compiler: $(CXXCUDA)"
ifdef CCAP
	@echo "Compute Capability: $(CCAP)"
else
	@echo "Compute Capability: Multi-arch (75, 80, 86, 89)"
endif
ifdef gpu
	@echo "GPU Support: Enabled"
else
	@echo "GPU Support: Disabled"
endif

.PHONY: all clean info
