import json
import time
import os
import datetime
from scanf import scanf
from natsort import natsorted, natsort_key


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def getOutVideoContext():
    OutVideoContext = {
        "folder_record" : "",
        "timestamp_begin" : 0,
        "timestamp_end" : 0,
        "format_input_folder_name" : "",
        "format_input_video_name" : "",
        "folder_out" : "",
        "file_out" : "",
    }
    return OutVideoContext

def split_video(video_file, video_format_name, timestamp_begin, timestamp_end, video_out):
    arr_p = video_file.split("/")
    name_video = arr_p[-1]
    values_list = scanf(video_format_name, name_video)
    t_obj_begin_file = datetime.datetime.fromtimestamp(values_list[0])
    t_obj_end_file = datetime.datetime.fromtimestamp(values_list[1])

    str_time_begin = None
    str_time_end = None
    if timestamp_begin != 0:
        t_obj_begin = datetime.datetime.fromtimestamp(timestamp_begin)
        _hour = abs(t_obj_begin.hour - t_obj_begin_file.hour)
        _minute = abs(t_obj_begin.minute - t_obj_begin_file.minute)
        _second = abs(t_obj_begin.second - t_obj_begin_file.second -3)
        str_time_begin = "{0}:{1}:{2}".format(_hour, _minute, _second)
        print(str_time_begin)
    if timestamp_end != 0:
        t_obj_end = datetime.datetime.fromtimestamp(timestamp_end)
        _hour = abs(t_obj_end.hour - t_obj_begin_file.hour)
        _minute = abs(t_obj_end.minute - t_obj_begin_file.minute)
        _second = abs(t_obj_end.second - t_obj_begin_file.second - 3)
        str_time_end = "{0}:{1}:{2}".format(_hour, _minute, _second)

    command = ""
    if str_time_begin != None and str_time_end != None: 
        command = "ffmpeg -y -i {0} -ss {1} -to {2} -c copy {3}".format(video_file, str_time_begin, str_time_end, video_out)
    elif str_time_begin == None: 
        command = "ffmpeg -y -i {0} -to {1} -c copy {2}".format(video_file, str_time_end, video_out)
    elif str_time_end == None: 
        command = "ffmpeg -y -i {0} -ss {1} -c copy {2}".format(video_file, str_time_begin, video_out)
    print(command)
    os.system(command)


def merger_video(file_log, video_out):
    command = "ffmpeg -f concat -safe 0 -i {0} -c copy {1} &".format(file_log, video_out);
    os.system(command)

def check_time_in_file(video_file, video_format_name, time):
    arr_p = video_file.split("/")
    name_video = arr_p[-1]
    values_list = scanf(video_format_name, name_video)

    if values_list[0] == 0 or values_list[1] == 0:
        return False 

    if time >= values_list[0] and time <= values_list[1]:
        return True
    return False 

def check_file_in_duration(video_file, video_format_name, timebegin, timeend):
    arr_p = video_file.split("/")
    name_video = arr_p[-1]
    values_list = scanf(video_format_name, name_video)

    if values_list[0] == 0 or values_list[1] == 0:
        return False 

    if values_list[0] >= timebegin and values_list[1] <= timeend:
        return True
    return False

def get_video_record_by_time(out_video_context):
    if out_video_context["timestamp_end"] <= out_video_context["timestamp_begin"]:
        return None

    folder_begin = ""
    folder_end = ""

    dt_obj_begin = datetime.datetime.fromtimestamp(out_video_context["timestamp_begin"])
    dt_obj_end = datetime.datetime.fromtimestamp(out_video_context["timestamp_end"])

    children= [os.path.join(out_video_context["folder_record"], child) for child in os.listdir(out_video_context["folder_record"])]
    directories= filter(os.path.isdir, children)

    #Convert dir to datetime obj
    list_dt_dir_obj = []
    for dir in directories:
        arr_p = dir.split("/")
        name_dir = arr_p[-1]
        _date_format = out_video_context["format_input_folder_name"] + " %H:%M:%S"
        f_dt_obj = datetime.datetime.strptime(name_dir + " 00:00:00", _date_format)
        list_dt_dir_obj.append(f_dt_obj)

    #Sort
    sort_list_dt_dir_obj = sorted(list_dt_dir_obj)

    #Get dir timebegin and timeend
    count_loop = 0
    for dt_dir in sort_list_dt_dir_obj:
        count_loop+=1
        #Find folder begin
        if folder_begin == "":
            if dt_obj_begin.date() == dt_dir.date():
                folder_begin = dt_dir.strftime(out_video_context["format_input_folder_name"])
            elif dt_obj_begin.date() < dt_dir.date():
                _dt_obj_begin = dt_dir
                if _dt_obj_begin.date() <= dt_obj_end.date():
                    dt_obj_begin = _dt_obj_begin
                    folder_begin = dt_dir.strftime(out_video_context["format_input_folder_name"])
                else:
                    return None

        #Find folder end
        if folder_end == "":
            if dt_obj_end.date() == dt_dir.date():
                folder_end = dt_dir.strftime(out_video_context["format_input_folder_name"])

        if folder_begin != "" and folder_end != "":
            break

    if folder_end == "":
        dt_dir_end = None
        for dt_dir in sort_list_dt_dir_obj:
            if dt_dir >= dt_obj_begin and dt_dir <= dt_obj_end:
                dt_dir_end = dt_dir
                folder_end = dt_dir.strftime(out_video_context["format_input_folder_name"])                
        if folder_end == "":
            return None

        if dt_dir_end is not None:
            dt_obj_end= datetime.datetime(year = dt_dir_end.year, month = dt_dir_end.month, day = dt_dir_end.day, 
                hour=23, minute=59, second=59)

    print(folder_begin)     
    print(folder_end)

    print(dt_obj_begin)     
    print(dt_obj_end)

    #Get file time begin
    path_folder_begin = ""
    if out_video_context["folder_record"][-1] == "/":
        path_folder_begin =  out_video_context["folder_record"] + folder_begin
    else:
        path_folder_begin =  out_video_context["folder_record"] + "/" + folder_begin
    children_begin = [os.path.join(path_folder_begin, child) for child in os.listdir(path_folder_begin)]
    directories_begin = filter(os.path.isfile, children_begin)
    file_begin = ""
    for file in directories_begin:
        ret = check_time_in_file(file, out_video_context["format_input_video_name"], int(dt_obj_begin.timestamp()))
        if ret == True:
            file_begin = file
            break    

    #Split file begin
    if file_begin == "":
        return None
    arr_p = file_begin.split("/")
    name_video_begin = arr_p[-1]
    values_list = scanf(out_video_context["format_input_video_name"], name_video_begin)
    video_begin_split = ""
    if out_video_context["folder_out"][-1] == "/":
        video_begin_split = "{0}{1}_{2}.mp4".format(out_video_context["folder_out"], int(dt_obj_begin.timestamp()), values_list[1]) 
    else:
        video_begin_split = "{0}/{1}_{2}.mp4".format(out_video_context["folder_out"], int(dt_obj_begin.timestamp()), values_list[1]) 
    print("video_begin_split = ", video_begin_split)
    if int(dt_obj_begin.timestamp()) >  values_list[0]:
        split_video(file_begin,out_video_context["format_input_video_name"], int(dt_obj_begin.timestamp()), 0, video_begin_split)

    #Get file time end
    path_folder_begin = ""
    if out_video_context["folder_record"][-1] == "/":
        path_folder_begin =  out_video_context["folder_record"] + folder_end
    else:
        path_folder_begin =  out_video_context["folder_record"] + "/" + folder_end
    children_begin = [os.path.join(path_folder_begin, child) for child in os.listdir(path_folder_begin)]
    directories_begin = filter(os.path.isfile, children_begin)
    file_end = ""
    for file in directories_begin:
        ret = check_time_in_file(file, out_video_context["format_input_video_name"], int(dt_obj_end.timestamp()))
        if ret == True:
            file_end = file
            break

    #Split file end
    if file_end == "":
        return None
    arr_p = file_end.split("/")
    name_video_end = arr_p[-1]
    values_list = scanf(out_video_context["format_input_video_name"], name_video_end)
    print(values_list)
    video_end_split = ""
    print(out_video_context["folder_out"])
    print(dt_obj_end.timestamp())
    print(values_list[1])
    if out_video_context["folder_out"][-1] == "/":
        video_end_split = "{0}{1}_{2}.mp4".format(out_video_context["folder_out"], int(dt_obj_end.timestamp()), values_list[1]) 
    else:
        video_end_split = "{0}/{1}_{2}.mp4".format(out_video_context["folder_out"], int(dt_obj_end.timestamp()), values_list[1]) 
    print("video_end_split = ", video_end_split)
    if int(dt_obj_end.timestamp()) <  values_list[1]:
        split_video(file_end,out_video_context["format_input_video_name"], int(dt_obj_end.timestamp()), 0, video_end_split)
    
    #Find files in duration
    count_days = 0
    files_find = []
    while True:
        dt_obj_folder_find = dt_obj_begin + datetime.timedelta(days=count_days)
        if dt_obj_folder_find > dt_obj_end:
            break
        count_days+=1

        folder_find = dt_obj_folder_find.strftime(out_video_context["format_input_folder_name"])       
        path_folder = ""
        if out_video_context["folder_record"][-1] == "/":
            path_folder =  out_video_context["folder_record"] + folder_find
        else:
            path_folder =  out_video_context["folder_record"] + "/" + folder_find
        children_find = [os.path.join(path_folder, child) for child in os.listdir(path_folder)]
        directories_find = filter(os.path.isfile, children_find)
        for file in directories_find:
            ret_check = check_file_in_duration(file, out_video_context["format_input_video_name"], int(dt_obj_begin.timestamp()), int(dt_obj_end.timestamp()))
            if ret_check is True:
                # print(file)
                files_find.append(file)

    #Sort fined files
    # for f in files_find:
    #     arr_p_f = f.split("/")
    #     name_video = arr_p_f[-1]
    #     values_list_v = scanf(out_video_context["format_input_video_name"], name_video)
    sort_files_find = sorted(files_find, key=natsort_key)
    
    #Create tmp file list
    sort_files_find.insert(0, video_begin_split)
    sort_files_find.append(video_end_split)
    print(sort_files_find)
    path_f_tmp = ""
    if out_video_context["folder_out"][-1] == "/":
        path_f_tmp =  out_video_context["folder_out"] + "tmp_list.txt"
    else:
        path_f_tmp =  out_video_context["folder_out"] + "/tmp_list.txt"
    f_tmp = open(path_f_tmp, "w")
    for f in sort_files_find:
        f_tmp.write("file '{0}'\n".format(f))
    f_tmp.close()

    video_out = ""
    video_out_name  = out_video_context["file_out"]
    if out_video_context["folder_out"][-1] == "/":
        video_out =  out_video_context["folder_out"] + video_out_name
    else:
        video_out =  out_video_context["folder_out"] + "/" + video_out_name
    merger_video(path_f_tmp, out_video_context["file_out"])

if __name__ == '__main__':
    time_begin = "2023-10-13 00:15:30"
    time_end = "2023-10-13 03:30:40"

    date_obj_begin = datetime.datetime.strptime(time_begin, DATE_FORMAT)
    date_obj_end = datetime.datetime.strptime(time_end, DATE_FORMAT)

    out_video_context = getOutVideoContext()
    out_video_context["folder_record"] = "/home/mq/playback"
    out_video_context["timestamp_begin"] = date_obj_begin.timestamp()
    out_video_context["timestamp_end"] = date_obj_end.timestamp()
    out_video_context["format_input_folder_name"] = "%Y_%m_%d"
    out_video_context["format_input_video_name"] = "%d_%d.mp4"
    out_video_context["folder_out"] = "/home/mq/playback"
    out_video_context["file_out"] = "video_playback_" + str(out_video_context["timestamp_begin"]) + "_" + str(out_video_context["timestamp_end"]) + ".mkv"

    get_video_record_by_time(out_video_context)
