__author__ = 'bloggins'

from construct import *
import os
import six

# Most up-to-date reference on Mach-O file format is at
# https://llvm.org/svn/llvm-project/llvm/trunk/include/llvm/Support/MachO.h
# http://www.opensource.apple.com/source/xnu/xnu-1456.1.26/EXTERNAL_HEADERS/mach-o/loader.h - less complete

# Official documentation from Apple:
# https://developer.apple.com/library/mac/Documentation/DeveloperTools/Conceptual/MachORuntime/index.html

def cpu_type_t(name, little_endian=True):
    field = ULInt32(name)
    if not little_endian:
        field = UBInt32(name)

    return Enum(field,
                CPU_TYPE_I386=7,
                CPU_TYPE_X86_64=0x1000000 | 7,
                CPU_TYPE_ARM=12,
                CPU_TYPE_POWERPC=18,
                CPU_ARCH_ABI64=0x1000000,
                CPU_TYPE_POWERPC64=0x1000000 | 18,
                )


def cpu_subtype_t(name, little_endian=True):
    field = ULInt32(name)
    if not little_endian:
        field = UBInt32(name)

    return Enum(field,
                CPU_SUBTYPE_I386_ALL=3,
                )

mach_header = Struct("mach_header",
                     # TODO: Validate magic and control struct endianness
                     UBInt32("magic"),
                     cpu_type_t("cputype"),
                     cpu_subtype_t("cpusubtype"),
                     Enum(ULInt32("filetype"),
                          MH_OBJECT=0x1,
                          MH_DYLIB=0x6,
                          ),
                     ULInt32("ncmds"),
                     ULInt32("sizeofcmds"),
                     FlagsEnum(ULInt32("flags"),
                               MH_NOUNDEFS=0x1,
                               MH_DYLDLINK=0x4,
                               MH_TWOLEVEL=0x80,
                               ),
                     If(lambda ctx: ctx.cputype == "CPU_TYPE_X86_64", ULInt32("reserved")))

uuid_command = Struct("uuid_command",
                      Array(16, ULInt8("uuid")))

section_64 = Struct("section_64",
                    String("sectname", length=16, padchar=six.b("\x00")),
                    String("segname", length=16, padchar=six.b("\x00")),
                    ULInt64("addr"),
                    ULInt64("size"),
                    ULInt32("offset"),
                    ULInt32("align"),
                    ULInt32("reloff"),
                    ULInt32("nreloc"),
                    ULInt32("flags"),
                    ULInt32("reserved1"),
                    ULInt32("reserved2"),
                    ULInt32("reserved3"),
                    )

segment_command_64 = Struct("segment_command_64",
                            String("segname", length=16, padchar=six.b("\x00")),
                            ULInt64("vmaddr"),
                            ULInt64("vmsize"),
                            ULInt64("fileoff"),
                            ULInt64("filesize"),
                            ULInt32("maxprot"),  #?
                            ULInt32("initprot"), #?
                            ULInt32("nsects"),
                            ULInt32("flags"),
                            Array(lambda ctx: ctx.nsects, section_64)
                            )

load_command = Struct("load_command",
                      Enum(ULInt32("cmd"),
                           LC_SEGMENT=0x1,
                           LC_SYMTAB=0x2,
                           LC_DYSYMTAB=0xb,
                           LC_LOAD_DYLIB=0xc,
                           LC_ID_DYLIB=0xd,
                           LC_SEGMENT_64=0x19,
                           LC_UUID=0x1b,
                           LC_CODE_SIGNATURE=0x1d,
                           LC_SEGMENT_SPLIT_INFO=0x1e,
                           LC_REEXPORT_DYLIB=0x8000001f,
                           LC_DYLD_INFO_ONLY=0x80000022,

                           LC_VERSION_MIN_MACOSX=0x24,
                           LC_SOURCE_VERSION=0x2a,
                           LC_FUNCTION_STARTS=0x26,
                           LC_DATA_IN_CODE=0x29,
                           LC_DYLIB_CODE_SIGN_DRS=0x2b,
                           ),
                      ULInt32("cmdsize"),
                      Switch("command", lambda ctx: ctx.cmd, {
                          "LC_UUID": uuid_command,
                          "LC_SEGMENT_64": segment_command_64,

                      }, default=OnDemand(Field("data", lambda ctx: ctx.cmdsize-8))),
                      )

mach_image = Struct("mach_image",
                    mach_header,
                    Array(lambda ctx: ctx.mach_header.ncmds, load_command))

fat_header = Struct("fat_header",
                    Magic(six.b("\xCA\xFE\xBA\xBE")),
                    UBInt32("nfat_arch"))

fat_arch = Struct("fat_arch",
                  cpu_type_t("cputype", little_endian=False),
                  cpu_subtype_t("cpusubtype", little_endian=False),
                  UBInt32("offset"),
                  UBInt32("size"),
                  UBInt32("align"),

                  Pointer(lambda ctx: ctx.offset, mach_image))

universal_file = Struct("universal_file",
                        fat_header,
                        Array(lambda ctx: ctx.fat_header.nfat_arch,
                              fat_arch,
                              ))


def main():
    #test_file = "/System/Library/Frameworks/OpenGL.framework/Versions/A/OpenGL"
    print "Current working directory is %s" % os.getcwd()
    test_file = "test/minimal.o"
    if not os.path.exists(test_file):
        print "Test file not found"
        exit(1)

    f = open(test_file, "rb")
    #obj = universal_file.parse_stream(f) # For executables and dylibs
    obj = mach_image.parse_stream(f)
    f.close()

    #print "%s is a Mach-O Universal Binary with %d architectures" % (os.path.basename(test_file), obj.fat_header.nfat_arch)

    print obj


if __name__ == "__main__":
    main()
