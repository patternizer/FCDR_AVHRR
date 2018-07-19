! * Copyright (C) 2017 J.Mittaz University of Reading
! * This code was developed for the EC project Fidelity and Uncertainty in
! * Climate Data Records from Earth Observations (FIDUCEO).
! * Grant Agreement: 638822
! *
! * This program is free software; you can redistribute it and/or modify it
! * under the terms of the GNU General Public License as published by the Free
! * Software Foundation; either version 3 of the License, or (at your option)
! * any later version.
! * This program is distributed in the hope that it will be useful, but WITHOUT
! * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
! * FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
! * more details.
! *
! * A copy of the GNU General Public License should have been supplied along
! * with this program; if not, see http://www.gnu.org/licenses/
! * ---------------------------------------------------------------------------

! * MT: 16-11-2017: fix for excess nArgs due to repeat orbits now applied in equator_to_equator.py

PROGRAM Extract_L1b_Data

  USE GbcsErrorHandler
  USE NOAA_LoadAVHRRLevel1B 
  USE Combine_Orbits

  IMPLICIT NONE

  CALL TopLevel()

CONTAINS

  SUBROUTINE TopLevel()

    INTEGER :: nArgs
    INTEGER :: nFiles
    INTEGER :: stat
    CHARACTER(LEN=256) :: file1
    CHARACTER(LEN=256) :: file2
    CHARACTER(LEN=256) :: file3
    CHARACTER(LEN=256) :: file4
    CHARACTER(LEN=256) :: file5
    CHARACTER(LEN=256) :: ofile
    CHARACTER(LEN=256) :: n_file
    CHARACTER(LEN=256) :: uuid_in
    CHARACTER(LEN=256) :: instr_str
    CHARACTER(LEN=256) :: y1
    CHARACTER(LEN=256) :: m1
    CHARACTER(LEN=256) :: d1
    CHARACTER(LEN=256) :: h1
    CHARACTER(LEN=256) :: min1
    CHARACTER(LEN=256) :: y2
    CHARACTER(LEN=256) :: m2
    CHARACTER(LEN=256) :: d2
    CHARACTER(LEN=256) :: h2
    CHARACTER(LEN=256) :: min2
    CHARACTER(LEN=256) :: sngle_split
    CHARACTER(LEN=256) :: walt_only
    CHARACTER(LEN=256) :: keeptemp
    CHARACTER(LEN=256) :: writefcdr
    INTEGER :: year1, month1, day1, hour1, minute1
    INTEGER :: year2, month2, day2, hour2, minute2
    TYPE(AVHRR_Data) :: AVHRR
    INTEGER :: instr
    TYPE(AVHRR_Radiative_Coefs) :: avhrr_rad_coefs
    CHARACTER(LEN=1) :: first_segment_input
    LOGICAL :: first_segment
    LOGICAL :: new_filename
    LOGICAL :: split_single_file
    LOGICAL :: walton_only
    CHARACTER(LEN=256) :: pygac1
    CHARACTER(LEN=256) :: pygac2
    CHARACTER(LEN=256) :: pygac3
    CHARACTER(LEN=256) :: pygac4
    CHARACTER(LEN=256) :: pygac5
    INTEGER :: IOS
    CHARACTER(LEN=256) :: gbcs_l1c_c
    LOGICAL :: gbcs_l1c
    LOGICAL :: gbcs_l1c_cal
    LOGICAL :: keep_temp
    LOGICAL :: write_fcdr

!MT: 26-10-2017: extract list of input arguments: 
!    INTEGER :: i
!    CHARACTER(LEN=256) :: temp
!    nArgs = COMMAND_ARGUMENT_COUNT()
!    write(*,*)'nArgs=',nArgs
!    DO i = 1,nArgs
!        CALL GET_COMMAND_ARGUMENT(i,temp,STATUS=stat)
!        write(*,*),'inArgs=',temp
!    ENDDO

    nArgs = COMMAND_ARGUMENT_COUNT()
    IF( 18 .gt. nArgs .or. 28 .le. nArgs )THEN
       write(*,*)'nArgs=',nArgs
       CALL Gbcs_Critical(.TRUE.,&
            'USAGE: ./extract_l1b_data.exe uuid outfile gbcs_l1c(Y/N/C) &
            &eq_year1 eq_month1 &
            &eq_day1 eq_hour1 eq_min1 eq_year2 eq_month2 eq_day2 eq_hour2 &
            &eq_min2 split_single walton_only keep_temp write_fcdr &
            &nfile file1 (file2) (file3) &
            &(file4) (file5) pygac1 (pygac2) (pygac3) (pygac4) (pygac5)',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(1,uuid_in,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get first command line argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(2,ofile,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get instr argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(3,gbcs_l1c_c,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get GBCS_L1C argument',&
            'Main','extract_l1b_data.f90')
    ENDIF
    IF( gbcs_l1c_c .eq. 'Y' .or. gbcs_l1c_c .eq. 'y' )THEN
       gbcs_l1c = .TRUE.
       gbcs_l1c_cal = .FALSE.
    ELSE IF( gbcs_l1c_c .eq. 'C' .or. gbcs_l1c_c .eq. 'c' )THEN
       gbcs_l1c = .TRUE.
       gbcs_l1c_cal = .TRUE.
    ELSE
       gbcs_l1c = .FALSE.
       gbcs_l1c_cal = .FALSE.
    ENDIF

    CALL GET_COMMAND_ARGUMENT(4,y1,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get year1 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(5,m1,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get month1 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(6,d1,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get day1 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(7,h1,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get hour1 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(8,min1,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get minute1 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(9,y2,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get year2 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(10,m2,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get month2 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(11,d2,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get day2 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(12,h2,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get hour2 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(13,min2,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get minute2 argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(14,sngle_split,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get sngle_split argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(15,walt_only,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get walton_only argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(16,keeptemp,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get keep_temp argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(17,writefcdr,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get write_fcdr argument',&
            'Main','extract_l1b_data.f90')
    ENDIF

    CALL GET_COMMAND_ARGUMENT(18,n_file,STATUS=stat)
    IF( 0 .ne. stat )THEN
       CALL Gbcs_Critical(.TRUE.,'Cannot get n_file command line argument',&
            'Main','extract_l1b_data.f90')
    ENDIF
    READ(n_file,*,IOSTAT=IOS)nfiles
    IF( 0 .ne. IOS )THEN
       CALL Gbcs_Critical(.TRUE.,'n_file cannot be parsed',&
            'Main','extract_l1b_data.f90')
    ENDIF

    IF( nArgs .ne. 18+nfiles*2 )THEN
       CALL Gbcs_Critical(.TRUE.,'nFiles not match no of input files/pygac',&
            'Main','extract_l1b_data.f90')
    ENDIF

    IF( 1 .eq. nfiles )THEN
       CALL GET_COMMAND_ARGUMENT(19,file1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(20,pygac1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
    ELSE IF( 2 .eq. nfiles )THEN
       CALL GET_COMMAND_ARGUMENT(19,file1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(20,file2,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(21,pygac1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(22,pygac2,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
    ELSE IF( 3 .eq. nfiles )THEN
       CALL GET_COMMAND_ARGUMENT(19,file1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(20,file2,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(21,file3,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file3 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(22,pygac1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(23,pygac2,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(24,pygac3,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
    ELSE IF( 4 .eq. nfiles )THEN
       CALL GET_COMMAND_ARGUMENT(19,file1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(20,file2,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(21,file3,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file3 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(22,file4,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file4 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(23,pygac1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(24,pygac2,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(25,pygac3,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac3 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(26,pygac4,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac4 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
    ELSE IF( 5 .eq. nfiles )THEN
       CALL GET_COMMAND_ARGUMENT(19,file1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(20,file2,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(21,file3,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file3 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(22,file4,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file4 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(23,file5,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get file5 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(24,pygac1,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac1 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(25,pygac2,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac2 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(26,pygac3,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac3 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(27,pygac4,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac4 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
       CALL GET_COMMAND_ARGUMENT(28,pygac5,STATUS=stat)
       IF( 0 .ne. stat )THEN
          CALL Gbcs_Critical(.TRUE.,'Cannot get pygac5 command line argument',&
               'Main','extract_l1b_data.f90')
       ENDIF
    ENDIF

    READ(y1,'(i4)')year1
    READ(m1,'(i4)')month1
    READ(d1,'(i4)')day1
    READ(h1,'(i4)')hour1
    READ(min1,'(i4)')minute1

    READ(y2,'(i4)')year2
    READ(m2,'(i4)')month2
    READ(d2,'(i4)')day2
    READ(h2,'(i4)')hour2
    READ(min2,'(i4)')minute2

    IF( 'Y' .eq. sngle_split .or. 'y' .eq. sngle_split )THEN
       split_single_file = .TRUE.
    ELSE
       split_single_file = .FALSE.
    ENDIF

    IF( 'Y' .eq. walt_only .or. 'y' .eq. walt_only )THEN
       walton_only = .TRUE.
    ELSE
       walton_only = .FALSE.
    ENDIF

    IF( 'Y' .eq. keeptemp .or. 'y' .eq. keeptemp )THEN
       keep_temp = .TRUE.
    ELSE
       keep_temp = .FALSE.
    ENDIF

    IF( 'Y' .eq. writefcdr .or. 'y' .eq. writefcdr )THEN
       write_fcdr = .TRUE.
    ELSE
       write_fcdr = .FALSE.
    ENDIF

    new_filename = .FALSE.
    IF( ofile .eq. 'TIROSN' )then
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA06' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA07' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA08' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA09' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA10' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA11' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA12' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA14' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA15' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA16' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA17' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA18' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'NOAA19' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'METOPA' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ELSE IF( ofile .eq. 'METOPB' )THEN
       instr_str = ofile
       new_filename = .TRUE.
    ENDIF
!FIDUCEO_FCDR_L1C_AVHRR1_NOAA08_19840106013100_19840106E03200_EASY_v0.1_fv0.1.nc
    IF( new_filename )THEN
!       WRITE(ofile,'(''FIDUCEO_FCDR_L1C_'',a,''_'',i4.4,i2.2,i2.2,i2.2,i2.2,&
!            &i2.2,''_'',i4.4,i2.2,i2.2,i2.2,i2.2,i2.2,''_EASY_v0.1_fv01.nc'')')&
!            TRIM(instr_str),year1,month1,day1,hour1,minute1,0,&
!            year2,month2,day2,hour2,minute2,0
       ofile = 'None'
    ENDIF
    !
    ! Note walton calibration for pre-beta
    !
    CALL read_all_data(nfiles,file1,file2,file3,file4,file5,uuid_in,&
         AVHRR,year1,month1,day1,hour1,minute1,year2,month2,day2,hour2,&
         minute2,ofile,.TRUE.,split_single_file,pygac1,pygac2,pygac3,&
         pygac4,pygac5,gbcs_l1c_output=gbcs_l1c,gbcs_l1c_cal=gbcs_l1c_cal,&
         walton_only=walton_only,keep_temp=keep_temp,write_fcdr=write_fcdr)
    !
    ! Deallocate structure
    !
    CALL Deallocate_OutData(AVHRR)

  END SUBROUTINE TopLevel

END PROGRAM EXTRACT_L1B_DATA

