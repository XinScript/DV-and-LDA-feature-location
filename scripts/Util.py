from os import makedirs,path

def create_folders(project_name):
    data_path = path.join(path.dirname(path.abspath(__file__)),'../datas', project_name)
    makedirs(data_path) if not path.exists(data_path) else None

    query_path = path.join(data_path, 'queries')
    makedirs(query_path) if not path.exists(query_path) else None

    goldset_class_path = path.join(data_path, 'goldsets', 'class')
    makedirs(goldset_class_path) if not path.exists(
        goldset_class_path) else None

    goldset_method_path = path.join(data_path, 'goldsets', 'method')
    makedirs(goldset_method_path) if not path.exists(
        goldset_method_path) else None

    d = {}
    d['data'] = data_path
    d['query'] = query_path
    d['class'] = goldset_class_path
    d['method'] = goldset_method_path
    return d


def obj_binary_search(objs, field, target):
        if target < getattr(objs[0], field):
            return -1

        lo, hi = 0, len(objs) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if target < getattr(objs[mid], field):
                hi = mid - 1
            elif target > getattr(objs[mid], field):
                lo = mid + 1
            else:
                return mid
        return lo
