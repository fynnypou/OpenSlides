import { Component } from '@angular/core';
import { BaseSlideComponent } from 'app/slides/base-slide-component';
import { UsersUserSlideData } from './users-user-slide-data';

@Component({
    selector: 'os-users-user-slide',
    templateUrl: './users-user-slide.component.html',
    styleUrls: ['./users-user-slide.component.scss']
})
export class UsersUserSlideComponent extends BaseSlideComponent<UsersUserSlideData> {
    public constructor() {
        super();
    }
}